from celery import shared_task

from apps.notifications.models import Notification
from apps.notifications.providers.email_provider import send_email


@shared_task
def send_email_task(notification_id: int):
    notification = Notification.objects.get(id=notification_id)

    send_email(
        to=notification.recipient,
        subject=notification.title,
        body=notification.message
    )