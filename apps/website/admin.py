from django.contrib import admin

from .models import ContactRequest


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'service', 'is_handled', 'created_at')
    list_filter = ('service', 'is_handled', 'created_at')
    search_fields = ('name', 'phone', 'email', 'message')
    list_editable = ('is_handled',)
    readonly_fields = ('created_at',)
