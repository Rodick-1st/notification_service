from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from rest_framework.test import APITestCase


class RateLimitTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u1",
            email="u1@example.com",
            password="pass12345",
        )
        self.client.force_authenticate(user=self.user)

    @patch("apps.notifications.services.notification_service.redis.Redis.from_url")
    def test_rate_limit_exceeded_returns_400(self, from_url):
        pipe = MagicMock()
        # results layout: total_incr, total_expire, ch_incr, ch_expire
        pipe.execute.return_value = [11, True, 1, True]

        client = MagicMock()
        client.pipeline.return_value = pipe
        from_url.return_value = client

        r = self.client.post(
            "/api/notifications/",
            {"title": "t", "message": "m", "channels": ["EMAIL"]},
            format="json",
        )

        self.assertEqual(r.status_code, 400)

