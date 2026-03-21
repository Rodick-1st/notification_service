from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.notifications.models import Notification, NotificationChannel, NotificationAttachment


class NotificationAttachmentsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u1",
            email="u1@example.com",
            password="pass12345",
        )
        self.client.force_authenticate(user=self.user)

        self.notification = Notification.objects.create(
            user=self.user,
            title="t",
            message="m",
        )
        self.channel = NotificationChannel.objects.create(
            notification=self.notification,
            channel_type="EMAIL",
        )

    def test_upload_attachment_creates_record(self):
        file = SimpleUploadedFile(
            name="doc.txt",
            content=b"hello",
            content_type="text/plain",
        )

        r = self.client.post(
            f"/api/notifications/{self.notification.id}/attachments/",
            {"file": file},
            format="multipart",
        )

        self.assertEqual(r.status_code, 201)
        self.assertEqual(NotificationAttachment.objects.filter(notification=self.notification).count(), 1)

    def test_upload_attachment_wrong_user_404(self):
        other = User.objects.create_user(
            username="u2",
            email="u2@example.com",
            password="pass12345",
        )
        self.client.force_authenticate(user=other)

        file = SimpleUploadedFile(
            name="doc.txt",
            content=b"hello",
            content_type="text/plain",
        )

        r = self.client.post(
            f"/api/notifications/{self.notification.id}/attachments/",
            {"file": file},
            format="multipart",
        )
        self.assertEqual(r.status_code, 404)

    def test_upload_attachment_invalid_type_400(self):
        file = SimpleUploadedFile(
            name="bad.bin",
            content=b"\x00\x01\x02",
            content_type="application/octet-stream",
        )

        r = self.client.post(
            f"/api/notifications/{self.notification.id}/attachments/",
            {"file": file},
            format="multipart",
        )
        self.assertEqual(r.status_code, 400)

