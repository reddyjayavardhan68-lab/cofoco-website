import uuid
from django.db import models
from django.contrib.auth.models import User

class Campaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    source = models.CharField(max_length=100)
    medium = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class AnalyticsEvent(models.Model):
    """Strictly pseudonymous storefront behavioral funnel events (AN01). Zero PII stored."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=100, db_index=True)
    event_name = models.CharField(max_length=50, db_index=True)
    character_id = models.CharField(max_length=100, blank=True, null=True)
    kit_id = models.CharField(max_length=100, blank=True, null=True)
    campaign_id = models.CharField(max_length=100, blank=True, null=True)
    metadata_json = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    changes_json = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
