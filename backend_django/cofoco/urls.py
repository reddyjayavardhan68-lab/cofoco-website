from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/catalog/', include('apps.catalog.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
]
