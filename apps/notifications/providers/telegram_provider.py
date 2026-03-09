class TelegramProvider:
    def send(self, chat_id: str, message: str) -> None:
        # Заглушка: здесь позже будет реальная интеграция с Telegram Bot API
        print(f"TELEGRAM -> {chat_id}: {message}")