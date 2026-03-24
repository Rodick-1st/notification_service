from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from django.test import override_settings

from apps.notifications.models import NotificationTemplate, Notification


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class NotificationTemplateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u1",
            email="u1@example.com",
            password="pass12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_notification_from_template(self):
        tpl = NotificationTemplate.objects.create(
            user=self.user,
            name="t1",
            title_template="Hello {{name}}",
            message_template="Your order {{order_id}} is ready",
        )

        response = self.client.post(
            "/api/notifications/",
            {
                "template_id": tpl.id,
                "context": {"name": "Alice", "order_id": 42},
                "channels": ["EMAIL"],
            },
            format="json",
        )
        print(response.status_code)
        print(response.data)
        self.assertEqual(response.status_code, 201)
        n = Notification.objects.get(title=response.data["title"])
        self.assertEqual(n.title, "Hello Alice")
        self.assertEqual(n.message, "Your order 42 is ready")
