from django.contrib import admin
from .models import Notification, NotificationChannel, DeliveryAttempt


admin.site.register(Notification)
admin.site.register(NotificationChannel)
admin.site.register(DeliveryAttempt)