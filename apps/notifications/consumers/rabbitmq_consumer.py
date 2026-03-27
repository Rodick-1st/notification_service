import json
import logging
import os
import time

import pika
from django.contrib.auth.models import User

from apps.notifications.enums import ChannelType
from apps.notifications.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "sups_ecom.events"
QUEUE_NAME = "notifications.queue"
DLQ_NAME = "notifications.dlq"


def get_or_create_system_user(email: str) -> User:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"username": email, "is_active": True},
    )
    if created:
        logger.info("Created system user for email: %s", email)
    return user


def _get_channels(user: User) -> list[str]:
    """Возвращает каналы доставки: email + telegram (chat_id захардкожен для тестов)."""
    return [ChannelType.EMAIL, ChannelType.TELEGRAM]


# ── Обработчики событий ────────────────────────────────────────────────────────

def handle_user_registered(payload: dict) -> None:
    email = payload["email"]
    user = get_or_create_system_user(email)
    NotificationService.create_notification(user, {
        "title": "Добро пожаловать!",
        "message": f"Вы успешно зарегистрировались на нашей платформе.",
        "channels": _get_channels(user),
    })


def handle_order_created(payload: dict) -> None:
    email = payload["email"]
    user = get_or_create_system_user(email)
    tx_ref = payload.get("tx_ref", "—")
    total = payload.get("total", 0)
    NotificationService.create_notification(user, {
        "title": "Заказ оформлен",
        "message": f"Ваш заказ #{tx_ref} на сумму {total} успешно оформлен.",
        "channels": _get_channels(user),
    })


def handle_review_created(payload: dict) -> None:
    email = payload["email"]
    user = get_or_create_system_user(email)
    product_name = payload.get("product_name", "")
    rating = payload.get("rating", "")
    NotificationService.create_notification(user, {
        "title": "Отзыв опубликован",
        "message": f"Ваш отзыв на товар «{product_name}» с оценкой {rating} успешно опубликован.",
        "channels": _get_channels(user),
    })


def handle_product_created(payload: dict) -> None:
    email = payload["email"]
    user = get_or_create_system_user(email)
    product_name = payload.get("product_name", "")
    category = payload.get("category", "")
    NotificationService.create_notification(user, {
        "title": "Товар добавлен",
        "message": f"Товар «{product_name}» в категории «{category}» успешно опубликован.",
        "channels": _get_channels(user),
    })


# ── Роутер событий ────────────────────────────────────────────────────────────

EVENT_HANDLERS = {
    "user.registered": handle_user_registered,
    "order.created": handle_order_created,
    "review.created": handle_review_created,
    "product.created": handle_product_created,
}


def on_message(channel, method, properties, body):
    try:
        message = json.loads(body)
        event_type = message.get("event_type")
        payload = message.get("payload", {})

        logger.info("Received event: %s", event_type)

        handler = EVENT_HANDLERS.get(event_type)
        if handler:
            handler(payload)
            channel.basic_ack(delivery_tag=method.delivery_tag)
        else:
            logger.warning("No handler for event: %s", event_type)
            channel.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as exc:
        logger.error("Failed to process message: %s", exc)
        # nack без requeue — сообщение уйдёт в DLQ
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


# ── Точка входа ───────────────────────────────────────────────────────────────

def run_consumer() -> None:
    params = pika.URLParameters(RABBITMQ_URL)

    retry_delay = 2
    max_delay = 30
    while True:
        try:
            connection = pika.BlockingConnection(params)
            break
        except Exception as exc:
            logger.warning("RabbitMQ not ready (%s), retrying in %ds...", exc, retry_delay)
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)

    channel = connection.channel()

    # Exchange
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True,
    )

    # Dead Letter Queue
    channel.queue_declare(queue=DLQ_NAME, durable=True)

    # Основная очередь с привязкой к DLQ
    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": DLQ_NAME,
        },
    )

    channel.queue_bind(
        queue=QUEUE_NAME,
        exchange=EXCHANGE_NAME,
        routing_key="#",
    )

    # Обрабатываем по одному сообщению — не берём следующее пока не ack'нули
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)

    logger.info("Waiting for events. Press CTRL+C to exit.")
    channel.start_consuming()
