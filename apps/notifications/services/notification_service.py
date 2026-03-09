from apps.notifications.models import Notification, NotificationChannel
from apps.notifications.tasks.send_notification import send_notification
from django.utils import timezone


class NotificationService:

    @staticmethod
    def create_notification(user, data):

        channels = data.pop("channels")

        notification = Notification.objects.create(
            user=user,
            **data
        )

        channel_objects = []

        for channel in channels:
            channel_objects.append(
                NotificationChannel(
                    notification=notification,
                    channel_type=channel
                )
            )

        NotificationChannel.objects.bulk_create(channel_objects)

        scheduled_at = notification.scheduled_at

        # отправляем задачу в Celery (с учётом scheduled_at)
        if scheduled_at and scheduled_at > timezone.now():
            send_notification.apply_async(args=[notification.id], eta=scheduled_at)
        else:
            send_notification.delay(notification.id)

        return notification