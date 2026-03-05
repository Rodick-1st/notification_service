from rest_framework import serializers
from .models import Notification, NotificationChannel
from .enums import ChannelType
from .services import NotificationService


class NotificationCreateSerializer(serializers.Serializer):

    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    scheduled_at = serializers.DateTimeField(required=False)
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=ChannelType.choices),
        allow_empty=False
    )

    def create(self, validated_data):
        return NotificationService.create_notification(
            user=self.context['request'].user,
            data=validated_data
        )


class NotificationChannelSerializer(serializers.ModelSerializer):

    class Meta:
        model = NotificationChannel
        fields = '__all__'


class NotificationListSerializer(serializers.ModelSerializer):

    channels = NotificationChannelSerializer(many=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "created_at",
            "scheduled_at",
            "channels",
        ]