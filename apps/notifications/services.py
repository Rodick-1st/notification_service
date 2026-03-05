from .models import Notification, NotificationChannel
from .enums import ChannelType


class NotificationService:

    @staticmethod
    def create_notification(user, data):

        channels = data.pop("channels")

        notification = Notification.objects.create(
            user=user,
            **data
        )

        channel_objects = []

        for channel in channels:

            channel_objects.append(
                NotificationChannel(
                    notification=notification,
                    channel_type=channel
                )
            )

        NotificationChannel.objects.bulk_create(channel_objects)

        return notification