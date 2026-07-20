from django.contrib import admin
from .models import MessageTemplate, MessageLog


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'channel', 'is_active')
    list_filter = ('template_type', 'channel')


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'status', 'sent_at', 'created_at')
    list_filter = ('status',)
