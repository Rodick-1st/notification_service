from celery import shared_task

from apps.notifications.models import Notification
from apps.notifications.providers.telegram_provider import send_telegram


@shared_task
def send_telegram_task(notification_id: int):
    notification = Notification.objects.get(id=notification_id)

    send_telegram(
        chat_id=notification.recipient,
        message=notification.message
    )