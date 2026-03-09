from django.contrib.auth.models import User
from rest_framework import serializers

from .models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    telegram_chat_id = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = User
        fields = ("username", "email", "password", "telegram_chat_id")

    def create(self, validated_data):
        telegram_chat_id = validated_data.pop("telegram_chat_id", "").strip()

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=validated_data["password"],
        )

        if telegram_chat_id:
            UserProfile.objects.create(
                user=user,
                telegram_chat_id=telegram_chat_id,
            )

        return user