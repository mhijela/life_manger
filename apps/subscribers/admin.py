from django.contrib import admin
from .models import Area, Subscriber


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')
    search_fields = ('name',)


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'area', 'status', 'monthly_price', 'created_at')
    list_filter = ('status', 'area')
    search_fields = ('full_name', 'phone', 'ip_address', 'mac_address')
