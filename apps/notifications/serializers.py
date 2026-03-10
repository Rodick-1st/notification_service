from rest_framework import serializers
from .models import Notification, NotificationChannel, NotificationTemplate
from .enums import ChannelType
from apps.notifications.services.notification_service import NotificationService


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = ("id", "name", "title_template", "message_template", "created_at")
        read_only_fields = ("id", "created_at")


class NotificationCreateSerializer(serializers.Serializer):

    title = serializers.CharField(max_length=255, required=False)
    message = serializers.CharField(required=False)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    template_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    context = serializers.JSONField(required=False, write_only=True)
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=ChannelType.choices),
        allow_empty=False, write_only=True
    )

    def validate(self, attrs):
        template_id = attrs.get("template_id")
        has_template = template_id is not None
        has_direct = bool(attrs.get("title")) and bool(attrs.get("message"))

        if has_template and has_direct:
            raise serializers.ValidationError(
                "Use either (title, message) OR (template_id, context)."
            )

        if not has_template and not has_direct:
            raise serializers.ValidationError(
                "Provide either (title, message) OR (template_id, context)."
            )

        return attrs

    def create(self, validated_data):
        return NotificationService.create_notification(
            user=self.context['request'].user,
            data=validated_data
        )


class NotificationChannelSerializer(serializers.ModelSerializer):

    class Meta:
        model = NotificationChannel
        fields = (
            "id",
            "channel_type",
            "status",
            "sent_at",
        )


class NotificationListSerializer(serializers.ModelSerializer):

    channels = NotificationChannelSerializer(many=True,read_only=True)

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