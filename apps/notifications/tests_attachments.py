from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.notifications.models import Notification, NotificationAttachment


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=False,
)
class NotificationAttachmentsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u1",
            email="u1@example.com",
            password="pass12345",
        )
        self.client.force_authenticate(user=self.user)

    def _post_notification(self, files=None, extra=None):
        payload = {
            "title": "t",
            "message": "m",
            "channels": ["EMAIL"],
        }
        if extra:
            payload.update(extra)
        data = {k: v for k, v in payload.items() if k != "channels"}
        data["channels"] = "EMAIL"
        # multipart cannot send JSON lists directly — use format="multipart"
        # channels must be sent as repeated key
        post_data = {
            "title": "t",
            "message": "m",
        }
        if files:
            for i, f in enumerate(files):
                post_data[f"files"] = f  # last one wins for single file; see below
            # For multiple files use a list
            if len(files) > 1:
                post_data["files"] = files
            else:
                post_data["files"] = files[0]

        return self.client.post(
            "/api/notifications/",
            {**post_data, "channels": "EMAIL"},
            format="multipart",
        )

    def test_upload_attachment_with_notification(self):
        file = SimpleUploadedFile(
            name="doc.txt",
            content=b"hello",
            content_type="text/plain",
        )

        with patch("apps.notifications.services.notification_service.send_notification") as mock_task:
            mock_task.delay.return_value = None
            mock_task.apply_async.return_value = None

            r = self.client.post(
                "/api/notifications/",
                {"title": "t", "message": "m", "channels": "EMAIL", "files": file},
                format="multipart",
            )

        self.assertEqual(r.status_code, 201)
        notification = Notification.objects.get(id=r.data["id"])
        self.assertEqual(NotificationAttachment.objects.filter(notification=notification).count(), 1)

    def test_upload_multiple_attachments(self):
        file1 = SimpleUploadedFile(name="a.txt", content=b"aaa", content_type="text/plain")
        file2 = SimpleUploadedFile(name="b.txt", content=b"bbb", content_type="text/plain")

        with patch("apps.notifications.services.notification_service.send_notification") as mock_task:
            mock_task.delay.return_value = None
            mock_task.apply_async.return_value = None

            r = self.client.post(
                "/api/notifications/",
                {"title": "t", "message": "m", "channels": "EMAIL", "files": [file1, file2]},
                format="multipart",
            )

        self.assertEqual(r.status_code, 201)
        notification = Notification.objects.get(id=r.data["id"])
        self.assertEqual(NotificationAttachment.objects.filter(notification=notification).count(), 2)

    def test_notification_without_attachments(self):
        with patch("apps.notifications.services.notification_service.send_notification") as mock_task:
            mock_task.delay.return_value = None
            mock_task.apply_async.return_value = None

            r = self.client.post(
                "/api/notifications/",
                {"title": "t", "message": "m", "channels": "EMAIL"},
                format="multipart",
            )

        self.assertEqual(r.status_code, 201)
        notification = Notification.objects.get(id=r.data["id"])
        self.assertEqual(NotificationAttachment.objects.filter(notification=notification).count(), 0)

    def test_invalid_file_type_returns_400(self):
        file = SimpleUploadedFile(
            name="bad.bin",
            content=b"\x00\x01\x02",
            content_type="application/octet-stream",
        )

        with patch("apps.notifications.services.notification_service.send_notification") as mock_task:
            mock_task.delay.return_value = None

            r = self.client.post(
                "/api/notifications/",
                {"title": "t", "message": "m", "channels": "EMAIL", "files": file},
                format="multipart",
            )

        self.assertEqual(r.status_code, 400)
        self.assertEqual(Notification.objects.count(), 0)
