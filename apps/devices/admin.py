from django.contrib import admin
from .models import Device, MaintenanceNote


class MaintenanceNoteInline(admin.TabularInline):
    model = MaintenanceNote
    extra = 0


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'device_type', 'ip_address', 'status', 'location')
    list_filter = ('device_type', 'status')
    search_fields = ('name', 'ip_address', 'serial_number')
    inlines = [MaintenanceNoteInline]
