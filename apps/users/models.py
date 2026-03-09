from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    telegram_chat_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="Telegram chat_id пользователя для отправки уведомлений",
    )

    def __str__(self) -> str:
        return f"Profile for {self.user.username}"
