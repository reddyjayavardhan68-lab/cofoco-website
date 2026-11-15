import uuid
from django.db import models
from django.contrib.auth.models import User

class Character(models.Model):
    STATUS_CHOICES = [('draft', 'Draft'), ('review', 'In Review'), ('published', 'Published')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=255)
    quality = models.CharField(max_length=100)
    routine_cue = models.CharField(max_length=255)
    story = models.TextField()
    theme_symbol = models.CharField(max_length=255)
    theme_colors_json = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    published_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    artwork_url = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} by COFOCO"

class Component(models.Model):
    CATEGORY_CHOICES = [('gym_essential', 'Gym Essential'), ('recovery', 'Recovery')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    material = models.CharField(max_length=255)
    dimensions = models.CharField(max_length=100, blank=True, null=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    supplier_name = models.CharField(max_length=150, blank=True, null=True)
    supplier_lead_days = models.IntegerField(default=7)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.sku}] {self.name}"

class Kit(models.Model):
    STATUS_CHOICES = [('draft', 'Draft'), ('published', 'Published')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=150)
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='kits')
    subtitle = models.CharField(max_length=255)
    description = models.TextField()
    routine_integration = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=True)
    image_url = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kit = models.ForeignKey(Kit, on_delete=models.CASCADE, related_name='variants')
    variant_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kit.name} - {self.variant_name}"

class BOMVersion(models.Model):
    STATUS_CHOICES = [('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='bom_versions')
    version = models.CharField(max_length=20, default='v1.0')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class BOMItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bom_version = models.ForeignKey(BOMVersion, on_delete=models.CASCADE, related_name='items')
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
