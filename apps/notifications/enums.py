from django.db import models


class ChannelType(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    TELEGRAM = "TELEGRAM", "Telegram"


class ChannelStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"