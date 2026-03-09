import requests
from django.conf import settings


class TelegramProvider:
    def send(self, chat_id: str, message: str) -> None:
        """
        Отправка сообщения в Telegram через Bot API.
        """
        if not settings.TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
        }

        response = requests.post(url, json=payload, timeout=10)

        if not response.ok:
            raise RuntimeError(
                f"Telegram API error: {response.status_code} {response.text}"
            )