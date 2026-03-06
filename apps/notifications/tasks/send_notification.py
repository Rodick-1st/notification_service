from celery import shared_task

from apps.notifications.models import Notification
from .registry import CHANNEL_TASKS


@shared_task
def send_notification(notification_id: int):
    notification = Notification.objects.get(id=notification_id)

    for channel in notification.channels.all():
        task = CHANNEL_TASKS.get(channel)

        if task:
            task.delay(notification_id)