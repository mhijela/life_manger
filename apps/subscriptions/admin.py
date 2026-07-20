from django.contrib import admin
from .models import Package, Subscription, SubscriptionHistory


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'speed', 'price', 'duration_value', 'duration_type', 'is_active')
    list_filter = ('is_active', 'duration_type')


class SubscriptionHistoryInline(admin.TabularInline):
    model = SubscriptionHistory
    extra = 0
    readonly_fields = ('action', 'date', 'created_by')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'package', 'start_date', 'end_date', 'status', 'price')
    list_filter = ('status',)
    search_fields = ('subscriber__full_name',)
    inlines = [SubscriptionHistoryInline]
