from django.contrib import admin
from .models import Unit, InventoryItem, StockMovement


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'unit', 'min_stock')
    list_filter = ('category',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('item', 'movement_type', 'quantity', 'date')
