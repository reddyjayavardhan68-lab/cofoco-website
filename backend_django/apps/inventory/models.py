import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.catalog.models import Component

class Inventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    component = models.OneToOneField(Component, on_delete=models.CASCADE, related_name='inventory')
    on_hand = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    location = models.CharField(max_length=100, default='Warehouse Bay A-1')
    updated_at = models.DateTimeField(auto_now=True)

class StockLedger(models.Model):
    CHANGE_TYPES = [
        ('receipt', 'Receipt'),
        ('reservation', 'Reservation'),
        ('pick', 'Pick'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name='ledger_entries')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES)
    quantity = models.IntegerField()
    balance_after = models.IntegerField()
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Reservation(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('consumed', 'Consumed'), ('released', 'Released')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=100, db_index=True)
    order_id = models.CharField(max_length=100, blank=True, null=True)
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
