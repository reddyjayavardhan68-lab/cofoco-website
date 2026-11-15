import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.catalog.models import ProductVariant

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('reconciliation_required', 'Reconciliation Required')
    ]
    ORDER_STATUS = [
        ('paid', 'Paid'),
        ('picking', 'Picking'),
        ('packed', 'Packed'),
        ('dispatched', 'Dispatched'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    customer_name = models.CharField(max_length=150)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    delivery_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS, default='pending')
    order_status = models.CharField(max_length=30, choices=ORDER_STATUS, default='paid')
    promised_dispatch_date = models.DateTimeField()
    assigned_staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    campaign_id = models.CharField(max_length=100, blank=True, null=True)
    session_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

class OrderItem(models.Model):
    """Preserves the exact purchased BOM configuration snapshot for warehouse pick lists!"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    kit_name = models.CharField(max_length=150)
    variant_name = models.CharField(max_length=100)
    character_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    bom_snapshot_json = models.TextField(help_text="Frozen snapshot of BOM components at moment of purchase")
    created_at = models.DateTimeField(auto_now_add=True)

class PaymentEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    gateway = models.CharField(max_length=50, default='razorpay')
    event_type = models.CharField(max_length=100)
    gateway_payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    gateway_order_id = models.CharField(max_length=100, blank=True, null=True)
    gateway_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=30)  # verified, duplicate, late_arrival, failed
    payload_json = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Shipment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipment')
    courier_name = models.CharField(max_length=100)
    tracking_number = models.CharField(max_length=100)
    tracking_url = models.URLField()
    dispatched_at = models.DateTimeField()
    delivered_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Return(models.Model):
    STATUS_CHOICES = [('requested', 'Requested'), ('received', 'Received'), ('inspected', 'Inspected'), ('rejected', 'Rejected')]
    INSPECTION_CHOICES = [('passed', 'Passed'), ('damaged', 'Damaged'), ('pending', 'Pending')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    inspection_result = models.CharField(max_length=20, choices=INSPECTION_CHOICES, default='pending')
    restocked = models.BooleanField(default=False)
    assigned_owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Refund(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_case = models.ForeignKey(Return, on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    gateway_refund_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, default='processed')
    reason = models.TextField()
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
