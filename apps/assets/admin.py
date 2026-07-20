from django.contrib import admin
from .models import AssetCategory, Asset, AssetHistory


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'serial_number', 'category', 'status', 'assigned_to')
    list_filter = ('status', 'category')


@admin.register(AssetHistory)
class AssetHistoryAdmin(admin.ModelAdmin):
    list_display = ('asset', 'action', 'date', 'subscriber')
