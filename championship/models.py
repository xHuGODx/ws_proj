from django.db import models
from django.conf import settings


class AdminBatchOperation(models.Model):
    kind = models.CharField(max_length=80)
    target_ref = models.CharField(max_length=120, blank=True)
    summary = models.CharField(max_length=255)
    metadata_json = models.JSONField(default=dict, blank=True)
    apply_sparql = models.TextField()
    rollback_sparql = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="admin_batch_operations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    rolled_back_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kind}: {self.summary}"
