from django.db import models
from django.contrib.auth.models import User


class IdempotencyRecord(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )
    key = models.CharField(max_length=128)
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=16, default="POST")
    request_hash = models.CharField(max_length=64)

    status_code = models.IntegerField()
    response_body = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "key", "endpoint", "method"],
                name="uniq_idempotency_user_key_endpoint_method",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.method} {self.endpoint} ({self.key})"
