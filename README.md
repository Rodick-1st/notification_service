# notification-service — Микросервис уведомлений

Самостоятельный Django-сервис для управления и доставки уведомлений через **Email** и **Telegram**. Изначально создавался как независимый проект — может использоваться отдельно или в связке с другими сервисами через RabbitMQ.

В текущей конфигурации интегрирован с [Ecommerce](https://github.com/Rodick-1st/E-commerce) — REST API интернет-магазина: принимает события о регистрации, заказах, отзывах и новых товарах, после чего доставляет уведомления пользователям.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Django](https://img.shields.io/badge/Django-6.0-green)
![DRF](https://img.shields.io/badge/DRF-3.16-red)
![Celery](https://img.shields.io/badge/Celery-5.6-brightgreen)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.13-orange)
![Redis](https://img.shields.io/badge/Redis-7--alpine-pink)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![JWT](https://img.shields.io/badge/Auth-JWT-yellow)
![OpenAPI](https://img.shields.io/badge/Docs-OpenAPI%203.0-lightgrey)

---

## Режимы работы

### Standalone (самостоятельный режим)

Сервис предоставляет REST API для создания уведомлений напрямую. Любой авторизованный пользователь (JWT) может:
- Отправить уведомление через Email / Telegram / оба канала
- Создать шаблон с `{{плейсхолдерами}}` и переиспользовать его
- Прикрепить файлы к уведомлению (PDF, PNG, JPEG, TXT, до 10 МБ)
- Запланировать отправку на определённое время (`scheduled_at`)

### Интеграция с внешним сервисом (event-driven)

Consumer подписывается на RabbitMQ exchange и автоматически создаёт уведомления при получении событий от внешнего сервиса.

```
 ┌──────────────────────────────────────┐      ┌─────────────────────────────────────────┐
 │       Standalone (REST API)          │      │             ecommerce (:8000)           │
 │                                      │      │                                         │
 │  POST /api/notifications/            │      │  Регистрация ──► "user.registered"      │
 │  {"channels": ["EMAIL","TELEGRAM"],  │  OR  │  Заказ       ──► "order.created"        │
 │   "scheduled_at": "...", ...}        │      │  Отзыв       ──► "review.created"       │
 │  Auth: JWT                           │      │  Новый товар ──► "product.created"      │
 └──────────────────┬───────────────────┘      └──────────────────────┬──────────────────┘
                    │                                                 ▼
                    │                              RabbitMQ — exchange: ecommerce.events
                    │                                     queue: notifications.queue
                    │                                          └── DLQ: notifications.dlq
                    │                                                 ▼
                    │                                   notification-service consumer
                    └──────────────────────────┬──────────────────────┘
                                               ▼
                               NotificationService.create_notification()
                               ├─ Idempotency-Key check (Redis)
                               ├─ Rate limiting (Redis)
                               ├─ Создание Notification + Channels в БД
                               └─ send_notification.delay() → Celery
                                               │
                               Celery Workers (Redis broker)
                                    ┌──────────┴───────────┐
                                    ▼                      ▼
                              send_email             send_telegram
                         (retry x3,cooldown 30s) (retry x3,cooldown 30s)
                                    │                      │
                              SMTP Yandex          Telegram Bot API
```

---

## Ключевые технические решения

| Решение | Описание |
|---|---|
| **Dual-mode архитектура** | Сервис работает и как REST API, и как event consumer — независимо |
| **Retry mechanism** | Celery повторяет доставку x3 с cooldown 30s; ошибки фиксируются в `DeliveryAttempt` |
| **Dead Letter Queue** | Необработанные RabbitMQ-сообщения не теряются — идут в `notifications.dlq` |
| **Exponential backoff** | Consumer переподключается к RabbitMQ с задержкой 2s → 4s → ... → 30s |
| **Rate limiting** | Redis-based лимиты на уровне сервиса — защита от спама |
| **Idempotency** | `Idempotency-Key` заголовок + SHA256 хеш тела запроса — безопасный retry |
| **Шаблоны** | `{{плейсхолдеры}}` в title/message с валидацией контекста при создании |
| **Вложения** | Файлы к уведомлениям (до 10 МБ, PDF/PNG/JPEG/TXT) |
| **Аудит доставки** | Полная история попыток: статус, ответ провайдера, timestamp |
| **Soft delete** | Уведомления скрываются флагом `is_deleted`, не удаляются из БД |

---

## Модели данных

```
User (Django built-in)
  └── (1) UserProfile
        └── telegram_chat_id

User (1)
  ├── (∞) Notification
  │         ├── title, message, scheduled_at, is_deleted
  │         │
  │         ├── (∞) NotificationChannel
  │         │         ├── channel_type: EMAIL | TELEGRAM
  │         │         ├── status: PENDING | SENT | FAILED
  │         │         ├── attempts_count, last_error, sent_at
  │         │         └── (∞) DeliveryAttempt
  │         │                   └── status, response, created_at
  │         │
  │         └── (∞) NotificationAttachment
  │                   └── file, filename, content_type, size
  │
  └── (∞) NotificationTemplate
            └── name, title_template, message_template
```

---

## Провайдеры доставки

### EmailProvider

- SMTP: `smtp.yandex.com:587`, TLS
- Поддерживает вложения (PDF, PNG, JPEG, TXT, до 10 МБ)
- При ошибке: Celery retry x3, cooldown 30s

### TelegramProvider

- Telegram Bot API через HTTP
- `chat_id` берётся из `UserProfile.telegram_chat_id`
- При ошибке: Celery retry x3, cooldown 30s

---

## Дополнительные механизмы

### Rate Limiting (Redis)

```python
NOTIFICATIONS_RATE_LIMIT_PER_MINUTE = 10        # Общий лимит
NOTIFICATIONS_RATE_LIMIT_PER_MINUTE_PER_CHANNEL = 5  # На канал
```

При превышении → `ValidationError("Rate limit exceeded")`

### Идемпотентность

```http
POST /notifications/
Idempotency-Key: unique-client-key-123
```

- SHA256-хеш тела запроса сравнивается с сохранённым
- Повторный запрос с тем же ключом → возвращает кешированный ответ
- Повторный запрос с другим телом → 400 Bad Request

### Шаблоны с плейсхолдерами

```json
{
    "name": "Подтверждение заказа",
    "title_template": "Заказ #{{tx_ref}} оформлен",
    "message_template": "Сумма: {{total}} руб. Спасибо, {{name}}!"
}
```

### Аудит доставки

Каждая попытка отправки записывается в `DeliveryAttempt`:
```
channel.attempts_count  — сколько раз пытались
channel.last_error      — текст последней ошибки
DeliveryAttempt.response — ответ провайдера
```

---

## Структура проекта

```
notification-service/
├── config/
│   ├── settings.py          # Django конфигурация (DB, Celery, Email, Telegram, Rate limits)
│   ├── celery.py            # Инициализация Celery
│   ├── urls.py              # Главная маршрутизация
│   └── wsgi.py
│
├── apps/
│   ├── core/
│   │   ├── models.py        # IdempotencyRecord — кэш идемпотентных запросов
│   │   └── views.py         # HealthCheckView GET /health/
│   │
│   ├── users/
│   │   ├── models.py        # UserProfile (telegram_chat_id)
│   │   └── views.py         # Регистрация, JWT login/refresh
│   │
│   └── notifications/
│       ├── models.py        # Notification, NotificationChannel, DeliveryAttempt,
│       │                    # NotificationTemplate, NotificationAttachment
│       ├── enums.py         # ChannelType (EMAIL/TELEGRAM), ChannelStatus (PENDING/SENT/FAILED)
│       ├── views.py         # ListCreate, Delete, Template CRUD
│       ├── serializers.py   # CreateNotificationSerializer, NotificationListSerializer
│       ├── urls.py          # API маршруты
│       │
│       ├── services/
│       │   └── notification_service.py  # Бизнес-логика: валидация, rate limit, создание
│       │
│       ├── tasks/
│       │   ├── send_notification.py     # Главная Celery задача (роутер по каналам)
│       │   ├── send_email.py            # Задача отправки Email
│       │   ├── send_telegram.py         # Задача отправки Telegram
│       │   └── registry.py             # {ChannelType → task}
│       │
│       ├── providers/
│       │   ├── email_provider.py        # SMTP клиент с поддержкой вложений
│       │   └── telegram_provider.py     # Telegram Bot API клиент
│       │
│       └── consumers/
│           └── rabbitmq_consumer.py     # RabbitMQ consumer + обработчики событий
│
├── management/commands/
│   └── run_consumer.py      # Django command: python manage.py run_consumer
│
├── pyproject.toml           # Poetry зависимости
├── Dockerfile.web           # Docker образ (web + consumer + worker)
└── .env.example
```

---

## Запуск в standalone режиме

```bash
#Скопируй `.env.example` в `.env` и заполни значения:
cp .env.example .env
#запуск контейнеров
docker compose up --build
```

### Поднимаются четыре контейнера:

| Сервис | Что делает                                                     |
|---|----------------------------------------------------------------|
| `db` | PostgreSQL 17                                                  |
| `redis` | Redis 7 (брокер Celery + rate limiting)                        |
| `web` | Django — выполняет `migrate`, затем стартует на `0.0.0.0:8000` |
| `worker` | Celery worker для отправки Email / Telegram                    |

### 3. Использование

После запуска доступны:

- **Swagger UI** → `http://127.0.0.1:8000/api/docs/`
- **REST API** → `http://127.0.0.1:8000/api/`

Быстрый старт через API:

```bash
# Регистрация
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "email": "user@example.com", "password": "pass1234", "telegram_chat_id": "123456789"}'

# Получение JWT-токена
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass1234"}'

# Отправка уведомления
curl -X POST http://127.0.0.1:8000/api/notifications/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Тест", "message": "Привет!", "channels": ["EMAIL", "TELEGRAM"]}'
```
---
### В составе ecommerce (Docker Compose)

Сервис подключается через `docker-compose.yml` в репозитории ecommerce: 

```bash
cd ecommerce
docker-compose up --build
```

Запускаются все 7 контейнеров: `ecommerce`, `notification`, `notification_worker`, `notification_consumer`, `rabbitmq`, `redis`, `postgres`

---
## Переменные окружения

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here

# PostgreSQL
POSTGRES_DB=notification_db
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

# Redis (Celery broker + rate limiting)
CELERY_BROKER_URL=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/0

# Email (SMTP)
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_smtp_app_password

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
CHAT_ID=telegram_chat_id

# RabbitMQ (только при интеграции)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Rate limiting (опционально, есть дефолты)
NOTIFICATIONS_RATE_LIMIT_PER_MINUTE=10
NOTIFICATIONS_RATE_LIMIT_PER_MINUTE_PER_CHANNEL=5

# Вложения (опционально)
NOTIFICATION_ATTACHMENT_MAX_BYTES=10485760
```

---
## Чему я научился

Проект дал опыт проектирования **надёжной системы доставки сообщений**:

- Реализация **dual-mode** сервиса: независимый REST API + event consumer в одном приложении
- Настройка **Celery** с retry-механизмом и мониторингом попыток доставки на уровне БД
- Проектирование **отказоустойчивого RabbitMQ consumer** с exponential backoff и DLQ
- Защита от дублей через **Idempotency-Key** с хешированием тела запроса
- **Rate limiting** на уровне Redis без сторонних библиотек

