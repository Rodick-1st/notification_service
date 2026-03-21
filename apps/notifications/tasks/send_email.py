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

    # считаем каждую попытку отправки
    channel.attempts_count += 1

    attachments = channel.notification.attachments.all()

    try:
        provider.send(
            to_email=channel.notification.user.email,
            subject=channel.notification.title,
            message=channel.notification.message,
            attachments=attachments,
        )

        channel.status = ChannelStatus.SENT
        channel.sent_at = timezone.now()
        channel.last_error = ""
        channel.save(update_fields=["status", "sent_at", "attempts_count", "last_error"])

        DeliveryAttempt.objects.create(
            notification_channel=channel,
            status=ChannelStatus.SENT,
            response="",
        )

    except Exception as exc:
        channel.status = ChannelStatus.FAILED
        channel.last_error = str(exc)
        channel.save(update_fields=["status", "attempts_count", "last_error"])

        DeliveryAttempt.objects.create(
            notification_channel=channel,
            status=ChannelStatus.FAILED,
            response=str(exc),
        )

        raise self.retry(exc=exc, countdown=30)