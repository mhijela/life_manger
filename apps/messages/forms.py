from django import forms
from .models import MessageTemplate

FC = {'class': 'form-control'}
FS = {'class': 'form-select'}


class SendMessageForm(forms.Form):
    recipient = forms.CharField(label='رقم الهاتف', widget=forms.TextInput(attrs=FC))
    message = forms.CharField(label='نص الرسالة', widget=forms.Textarea(attrs={**FC, 'rows': 4}))


class BulkMessageForm(forms.Form):
    status = forms.ChoiceField(
        label='حالة المشتركين',
        choices=[('', 'الكل'), ('active', 'نشط'), ('expired', 'منتهي'), ('debtor', 'مدين')],
        required=False,
        widget=forms.Select(attrs=FS),
    )
    template = forms.ModelChoiceField(
        queryset=MessageTemplate.objects.filter(is_active=True),
        label='القالب',
        widget=forms.Select(attrs=FS),
    )


class MessageTemplateForm(forms.ModelForm):
    class Meta:
        model = MessageTemplate
        fields = ['name', 'template_type', 'channel', 'body', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs=FC),
            'template_type': forms.Select(attrs=FS),
            'channel': forms.Select(attrs=FS),
            'body': forms.Textarea(attrs={**FC, 'rows': 5}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
