from django import forms
from apps.messages.models import MessageTemplate
from .models import SystemSettings


class SystemSettingsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['debt_sms_template'].queryset = MessageTemplate.objects.filter(
            template_type='debt_reminder',
            is_active=True,
        )

    class Meta:
        model = SystemSettings
        fields = [
            'company_name', 'logo', 'currency', 'currency_symbol',
            'subscription_alert_days', 'pagination_size', 'timezone',
            'sms_username', 'sms_api_key', 'sms_sender_id', 'sms_api_url',
            'jawwal_username', 'jawwal_password', 'jawwal_base_url',
            'jawwal_request_payment_url', 'jawwal_transfer_url', 'jawwal_field_map', 'jawwal_session_path',
            'cashbox_opening_balance', 'auto_suspend_on_expiry', 'auto_renew_enabled', 'debt_sms_template',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control'}),
            'subscription_alert_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'pagination_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control'}),
            'sms_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'sms_api_key': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password', 'render_value': True}),
            'sms_sender_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sender Name'}),
            'sms_api_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'http://int.mtcsms.com/sendsms.aspx'}),
            'jawwal_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'user@service'}),
            'jawwal_password': forms.PasswordInput(attrs={'class': 'form-control', 'render_value': True}),
            'jawwal_base_url': forms.URLInput(attrs={'class': 'form-control'}),
            'jawwal_request_payment_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/merchant/requestPaymentServices'}),
            'jawwal_transfer_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/merchant/transferMoneyServices'}),
            'jawwal_field_map': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': '{"request_payment": {...}}'}),
            'jawwal_session_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'tools/jawwal_sessions/default.json',
            }),
            'cashbox_opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'auto_suspend_on_expiry': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_renew_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'debt_sms_template': forms.Select(attrs={'class': 'form-select'}),
        }
