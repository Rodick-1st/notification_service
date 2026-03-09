from celery import shared_task

from django.utils import timezone

from apps.notifications.models import NotificationChannel, DeliveryAttempt
from apps.notifications.enums import ChannelStatus
from apps.notifications.providers.telegram_provider import TelegramProvider
from apps.users.models import UserProfile


@shared_task(bind=True, max_retries=3)
def send_telegram(self, notification_channel_id: int):
    channel = NotificationChannel.objects.select_related("notification").get(
        id=notification_channel_id
    )

    provider = TelegramProvider()

    channel.attempts_count += 1

    try:
        user = channel.notification.user

        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            raise RuntimeError("User profile with telegram_chat_id is not configured")

        if not profile.telegram_chat_id:
            raise RuntimeError("telegram_chat_id is empty for this user")

        provider.send(
            chat_id=profile.telegram_chat_id,
            message=channel.notification.message,
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