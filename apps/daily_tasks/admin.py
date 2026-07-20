from django.contrib import admin

from .models import DailyTask


@admin.register(DailyTask)
class DailyTaskAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'task_type',
        'scheduled_date',
        'scheduled_time',
        'status',
        'priority',
        'assigned_to',
    )
    list_filter = ('status', 'task_type', 'priority', 'scheduled_date')
    search_fields = (
        'title',
        'description',
        'location',
        'subscriber__full_name',
        'subscriber__phone',
    )
    autocomplete_fields = ('subscriber', 'device', 'assigned_to')
