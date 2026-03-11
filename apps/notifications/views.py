from rest_framework.generics import (
    ListCreateAPIView,
    DestroyAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
import hashlib
import json

from .models import Notification, NotificationTemplate
from .serializers import (
    NotificationCreateSerializer,
    NotificationListSerializer,
    NotificationTemplateSerializer,
)


class NotificationListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Notification.objects.filter(user=self.request.user, is_deleted=False)
            .prefetch_related("channels")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return NotificationCreateSerializer
        return NotificationListSerializer

    def create(self, request, *args, **kwargs):
        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            return super().create(request, *args, **kwargs)

        from apps.core.models import IdempotencyRecord

        endpoint = request.path
        method = request.method.upper()

        # stable-ish hash of request body
        body = request.data
        body_json = json.dumps(body, sort_keys=True, default=str, separators=(",", ":"))
        request_hash = hashlib.sha256(body_json.encode("utf-8")).hexdigest()

        existing = IdempotencyRecord.objects.filter(
            user=request.user,
            key=idem_key,
            endpoint=endpoint,
            method=method,
        ).first()

        if existing:
            if existing.request_hash != request_hash:
                raise ValidationError(
                    {"Idempotency-Key": ["Key already used with different request body."]}
                )
            return Response(existing.response_body, status=existing.status_code)

        response = super().create(request, *args, **kwargs)

        IdempotencyRecord.objects.create(
            user=request.user,
            key=idem_key,
            endpoint=endpoint,
            method=method,
            request_hash=request_hash,
            status_code=response.status_code,
            response_body=response.data,
        )

        return response


class NotificationDeleteView(DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user, is_deleted=False)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])


class NotificationTemplateListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationTemplateSerializer

    def get_queryset(self):
        return NotificationTemplate.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationTemplateDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationTemplateSerializer

    def get_queryset(self):
        return NotificationTemplate.objects.filter(user=self.request.user)
