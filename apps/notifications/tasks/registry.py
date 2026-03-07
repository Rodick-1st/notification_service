from apps.notifications.enums import ChannelType
from .send_email import send_email
from .send_telegram import send_telegram

CHANNEL_TASKS = {
    ChannelType.EMAIL: send_email,
    ChannelType.TELEGRAM: send_telegram,
}