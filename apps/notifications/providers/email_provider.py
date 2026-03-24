from django.conf import settings
from django.core.mail import EmailMessage, send_mail


class EmailProvider:
    def send(self, to_email: str, subject: str, message: str, attachments=None) -> None:
        """
        Отправка email через стандартный Django email backend.
        """
        if not settings.EMAIL_HOST_USER:
            raise RuntimeError("EMAIL_HOST_USER is not configured")

        if not attachments:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            return

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )

        # attachments ожидается как список NotificationAttachment
        for att in attachments:
            if not att.file:
                continue
            # file хранится локально в MEDIA_ROOT (MVP)
            with att.file.open("rb") as f:
                content = f.read()
            filename = att.filename or att.file.name
            mimetype = att.content_type or None
            email.attach(filename, content, mimetype)

        email.send(fail_silently=False)