from django.contrib import admin
from .models import Notification, NotificationChannel, DeliveryAttempt, NotificationTemplate


admin.site.register(Notification)
admin.site.register(NotificationChannel)
admin.site.register(DeliveryAttempt)
admin.site.register(NotificationTemplate)