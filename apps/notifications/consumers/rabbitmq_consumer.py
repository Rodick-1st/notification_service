import json
import logging
import os

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
    """Возвращает каналы доставки: всегда email, telegram — если есть chat_id."""
    channels = [ChannelType.EMAIL]
    if hasattr(user, "telegram_profile") and user.telegram_profile.chat_id:
        channels.append(ChannelType.TELEGRAM)
    return channels


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


def handle_seller_approved(payload: dict) -> None:
    email = payload["email"]
    user = get_or_create_system_user(email)
    business_name = payload.get("business_name", "")
    NotificationService.create_notification(user, {
        "title": "Ваша заявка одобрена",
        "message": f"Поздравляем! Магазин «{business_name}» одобрен и теперь активен.",
        "channels": _get_channels(user),
    })


# ── Роутер событий ────────────────────────────────────────────────────────────

EVENT_HANDLERS = {
    "user.registered": handle_user_registered,
    "order.created": handle_order_created,
    "seller.approved": handle_seller_approved,
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
    connection = pika.BlockingConnection(params)
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
