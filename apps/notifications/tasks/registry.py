from .send_email import send_email_task
from .send_telegram import send_telegram_task


CHANNEL_TASKS = {
    "email": send_email_task,
    "telegram": send_telegram_task,
}