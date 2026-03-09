class EmailProvider:
    def send(self, to_email: str, subject: str, message: str) -> None:
        # Заглушка: здесь позже будет реальная отправка через SMTP
        print(f"EMAIL -> {to_email}: {subject}")