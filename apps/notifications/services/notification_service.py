import re

from apps.notifications.models import Notification, NotificationChannel, NotificationTemplate
from apps.notifications.tasks.send_notification import send_notification
from django.utils import timezone
from rest_framework.exceptions import ValidationError


class NotificationService:

    _placeholder_re = re.compile(r"{{\s*(?P<key>[a-zA-Z_]\w*)\s*}}")

    @classmethod
    def _render_template(cls, template: str, context: dict) -> str:
        missing = []

        def replace(match: re.Match) -> str:
            key = match.group("key")
            if key not in context:
                missing.append(key)
                return match.group(0)
            value = context[key]
            return "" if value is None else str(value)

        rendered = cls._placeholder_re.sub(replace, template)

        if missing:
            raise ValidationError(
                {"context": [f"Missing keys for template: {sorted(set(missing))}"]}
            )

        return rendered

    @staticmethod
    def create_notification(user, data):

        channels = data.pop("channels")
        template_id = data.pop("template_id", None)
        context = data.pop("context", None) or {}

        if template_id is not None:
            tpl = NotificationTemplate.objects.filter(id=template_id, user=user).first()
            if not tpl:
                raise ValidationError({"template_id": ["Template not found."]})

            data["title"] = NotificationService._render_template(
                tpl.title_template, context
            )
            data["message"] = NotificationService._render_template(
                tpl.message_template, context
            )

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