from django.db import models
from django.contrib.auth.models import User
from .enums import ChannelType, ChannelStatus


class Notification(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=255)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    scheduled_at = models.DateTimeField(null=True, blank=True)

    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class NotificationChannel(models.Model):

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="channels"
    )

    channel_type = models.CharField(
        max_length=20,
        choices=ChannelType.choices
    )

    status = models.CharField(
        max_length=20,
        choices=ChannelStatus.choices,
        default=ChannelStatus.PENDING
    )

    attempts_count = models.IntegerField(default=0)

    last_error = models.TextField(blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.notification.id} - {self.channel_type}"


class DeliveryAttempt(models.Model):

    notification_channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE,
        related_name="attempts"
    )

    status = models.CharField(max_length=20)

    response = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)