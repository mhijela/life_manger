from django import forms
from apps.subscribers.models import Subscriber
from apps.settings_app.models import SystemSettings
from .models import MessageTemplate

FC = {'class': 'form-control'}
FS = {'class': 'form-select'}

OTHER_RECIPIENT = '__other__'
MSG_TEMPLATE = 'template'
MSG_CUSTOM = 'custom'


class SendMessageForm(forms.Form):
    recipient_choice = forms.ChoiceField(
        label='المستلم',
        widget=forms.Select(attrs={**FS, 'id': 'id_recipient_choice'}),
    )
    recipient = forms.CharField(
        label='رقم الهاتف',
        required=False,
        widget=forms.TextInput(attrs={
            **FC,
            'id': 'id_recipient',
            'placeholder': 'مثال: 0599123456',
            'dir': 'ltr',
            'inputmode': 'tel',
        }),
    )
    message_source = forms.ChoiceField(
        label='نص الرسالة',
        choices=[
            (MSG_TEMPLATE, 'اختيار قالب جاهز'),
            (MSG_CUSTOM, 'رسالة مكتوبة'),
        ],
        initial=MSG_TEMPLATE,
        widget=forms.RadioSelect(attrs={'id': 'id_message_source'}),
    )
    template = forms.ModelChoiceField(
        label='القالب',
        queryset=MessageTemplate.objects.none(),
        required=False,
        empty_label='— اختر قالباً —',
        widget=forms.Select(attrs={**FS, 'id': 'id_template'}),
    )
    message = forms.CharField(
        label='نص الرسالة المكتوبة',
        required=False,
        widget=forms.Textarea(attrs={**FC, 'rows': 4, 'id': 'id_message'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [('', '— اختر مشتركاً —'), (OTHER_RECIPIENT, 'رقم آخر (خارج القائمة)')]
        for sub in Subscriber.objects.order_by('full_name').only('id', 'full_name', 'phone'):
            phone = (sub.phone or '').strip()
            if not phone:
                continue
            label = f'{sub.full_name} — {phone}'
            choices.append((f'sub:{sub.pk}', label))
        self.fields['recipient_choice'].choices = choices
        self.fields['template'].queryset = MessageTemplate.objects.filter(is_active=True).order_by('name')

    def _resolve_subscriber(self, choice):
        if not choice or not choice.startswith('sub:'):
            return None
        try:
            pk = int(choice.split(':', 1)[1])
        except (TypeError, ValueError):
            return None
        return Subscriber.objects.filter(pk=pk).first()

    def _build_template_context(self, subscriber, phone):
        settings = SystemSettings.load()
        context = {
            'name': subscriber.full_name if subscriber else '',
            'phone': phone or '',
            'company': settings.company_name,
            'amount': '',
            'due_date': '',
            'total_amount': '',
            'expiry_date': '',
        }
        if subscriber:
            context['amount'] = subscriber.monthly_price or ''
            sub = (
                subscriber.active_subscription
                or subscriber.subscriptions.order_by('-end_date').first()
            )
            if sub:
                context['expiry_date'] = sub.end_date
                context['due_date'] = sub.end_date
                context['amount'] = sub.price
        return context

    def clean(self):
        cleaned = super().clean()
        choice = cleaned.get('recipient_choice')
        recipient = (cleaned.get('recipient') or '').strip()
        source = cleaned.get('message_source') or MSG_CUSTOM
        template = cleaned.get('template')
        message = (cleaned.get('message') or '').strip()
        subscriber = None

        if not choice:
            self.add_error('recipient_choice', 'اختر مشتركاً أو رقم آخر')
            return cleaned

        if choice == OTHER_RECIPIENT:
            if not recipient:
                self.add_error('recipient', 'أدخل رقم الهاتف')
                return cleaned
            cleaned['recipient'] = recipient
        elif choice.startswith('sub:'):
            subscriber = self._resolve_subscriber(choice)
            if not subscriber or not (subscriber.phone or '').strip():
                self.add_error('recipient_choice', 'المشترك لا يملك رقم هاتف')
                return cleaned
            cleaned['recipient'] = subscriber.phone.strip()
            cleaned['subscriber'] = subscriber
        else:
            self.add_error('recipient_choice', 'اختيار غير صالح')
            return cleaned

        phone = cleaned.get('recipient', '')

        if source == MSG_TEMPLATE:
            if not template:
                self.add_error('template', 'اختر قالباً')
                return cleaned
            context = self._build_template_context(subscriber, phone)
            cleaned['message'] = template.render(context)
            cleaned['selected_template'] = template
        else:
            if not message:
                self.add_error('message', 'اكتب نص الرسالة')
                return cleaned
            cleaned['message'] = message
            cleaned['selected_template'] = None

        return cleaned


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
