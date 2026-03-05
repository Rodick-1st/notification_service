from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated

from .models import Notification
from .serializers import NotificationCreateSerializer, NotificationListSerializer



class NotificationListCreateView(ListCreateAPIView):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Notification.objects
            .filter(user=self.request.user, is_deleted=False)
            .order_by("-created_at")
        )

    def get_serializer_class(self):

        if self.request.method == "POST":
            return NotificationCreateSerializer

        return NotificationListSerializer
