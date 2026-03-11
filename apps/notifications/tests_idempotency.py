from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from django.test import override_settings

from apps.notifications.models import Notification


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class IdempotencyTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u1",
            email="u1@example.com",
            password="pass12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_idempotent_create_returns_same_response(self):
        payload = {
            "title": "t",
            "message": "m",
            "channels": ["EMAIL"],
        }
        headers = {"HTTP_IDEMPOTENCY_KEY": "abc-123"}

        r1 = self.client.post("/api/notifications/", payload, format="json", **headers)
        self.assertEqual(r1.status_code, 201)

        r2 = self.client.post("/api/notifications/", payload, format="json", **headers)
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r1.data["title"], r2.data["title"])

        self.assertEqual(Notification.objects.count(), 1)

    def test_idempotent_create_rejects_different_body(self):
        headers = {"HTTP_IDEMPOTENCY_KEY": "abc-456"}

        r1 = self.client.post(
            "/api/notifications/",
            {"title": "t", "message": "m", "channels": ["EMAIL"]},
            format="json",
            **headers,
        )
        self.assertEqual(r1.status_code, 201)

        r2 = self.client.post(
            "/api/notifications/",
            {"title": "t2", "message": "m2", "channels": ["EMAIL"]},
            format="json",
            **headers,
        )
        self.assertEqual(r2.status_code, 400)
