from django.conf import settings
from django.core.mail import send_mail


class EmailProvider:
    def send(self, to_email: str, subject: str, message: str) -> None:
        """
        Отправка email через стандартный Django email backend.
        """
        if not settings.EMAIL_HOST_USER:
            raise RuntimeError("EMAIL_HOST_USER is not configured")

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )