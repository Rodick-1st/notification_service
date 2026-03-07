from celery import shared_task
from django.utils import timezone

from apps.notifications.models import NotificationChannel, DeliveryAttempt
from apps.notifications.enums import ChannelStatus
from apps.notifications.providers.email_provider import EmailProvider


@shared_task(bind=True, max_retries=3)
def send_email(self, notification_channel_id: int):

    channel = NotificationChannel.objects.select_related("notification").get(
        id=notification_channel_id
    )

    provider = EmailProvider()

    try:
        provider.send(
            to_email=channel.notification.user.email,
            subject=channel.notification.title,
            message=channel.notification.message,
        )

        channel.status = ChannelStatus.SENT
        channel.sent_at = timezone.now()
        channel.save(update_fields=["status", "sent_at"])

        DeliveryAttempt.objects.create(
            channel=channel,
            success=True,
        )

    except Exception as exc:

        DeliveryAttempt.objects.create(
            channel=channel,
            success=False,
            error=str(exc),
        )

        channel.status = ChannelStatus.FAILED
        channel.save(update_fields=["status"])

        raise self.retry(exc=exc, countdown=30)