from django import forms
from django.utils import timezone
from apps.subscriptions.models import Package
from .models import Subscriber, Area

FORM_CONTROL = {'class': 'form-control'}
FORM_SELECT = {'class': 'form-select'}
FORM_TEXTAREA = {'class': 'form-control', 'rows': 3}
FORM_CHECK = {'class': 'form-check-input'}


class SubscriberCreateForm(forms.Form):
    full_name = forms.CharField(
        label='اسم المشترك',
        max_length=200,
        widget=forms.TextInput(attrs=FORM_CONTROL),
    )
    phone = forms.CharField(
        label='رقم الجوال',
        max_length=20,
        widget=forms.TextInput(attrs={**FORM_CONTROL, 'dir': 'ltr', 'placeholder': '05xxxxxxxx'}),
    )
    pppoe_username = forms.CharField(
        label='اليوزر (PPPoE)',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={**FORM_CONTROL, 'dir': 'ltr'}),
    )
    pppoe_password = forms.CharField(
        label='الرقم السري (PPPoE)',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={**FORM_CONTROL, 'dir': 'ltr'}),
    )
    subscription_start_date = forms.DateField(
        label='تاريخ الاشتراك',
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={**FORM_CONTROL, 'type': 'date'}),
        help_text='مدة الاشتراك تُحسب من الباقة المختارة',
    )
    auto_renew = forms.BooleanField(
        label='تجديد شهري تلقائياً',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
        help_text='يتجدد الاشتراك تلقائياً حسب مدة الباقة — يمكن إيقافه من الإعدادات أو تعديل المشترك',
    )
    package_name = forms.CharField(
        label='الباقة',
        max_length=100,
        widget=forms.TextInput(attrs={
            **FORM_CONTROL,
            'id': 'package-name-input',
            'placeholder': 'اكتب اسم الباقة أو السرعة...',
            'autocomplete': 'off',
        }),
    )
    package_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'package-id-input'}),
    )
    create_new_package = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'create-new-package-input', 'value': '0'}),
    )
    new_package_speed = forms.CharField(
        label='سرعة الباقة الجديدة',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={**FORM_CONTROL, 'placeholder': 'مثال: 10 ميجا'}),
    )
    new_package_price = forms.DecimalField(
        label='سعر الباقة الافتراضي',
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={**FORM_CONTROL, 'step': '0.01'}),
        help_text='سعر الباقة في النظام — للباقات الجديدة فقط',
    )
    subscription_price = forms.DecimalField(
        label='سعر الاشتراك',
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={**FORM_CONTROL, 'step': '0.01', 'id': 'subscription-price-input'}),
        help_text='يُعبّأ من الباقة — يمكن تغييره لهذا المشترك',
    )

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if Subscriber.objects.filter(phone=phone).exists():
            raise forms.ValidationError('رقم الجوال مسجّل لمشترك آخر.')
        return phone

    def clean_package_id(self):
        value = (self.cleaned_data.get('package_id') or '').strip()
        if not value:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _resolve_existing_package(self, package_name):
        name = package_name.strip()
        if not name:
            return None

        package = Package.objects.filter(is_active=True, name__iexact=name).first()
        if package:
            return package

        package = Package.objects.filter(is_active=True, speed__iexact=name).first()
        if package:
            return package

        name_part = name.split('—')[0].split('-')[0].strip()
        if name_part and name_part != name:
            package = Package.objects.filter(is_active=True, name__iexact=name_part).first()
            if package:
                return package

        return None

    def _finalize_subscription_price(self, cleaned_data):
        package = cleaned_data.get('package')
        if not package:
            return cleaned_data

        subscription_price = cleaned_data.get('subscription_price')
        if subscription_price is None:
            subscription_price = package.price
        cleaned_data['subscription_price'] = subscription_price
        return cleaned_data

    def clean(self):
        cleaned_data = super().clean()
        package_id = cleaned_data.get('package_id')
        package_name = (cleaned_data.get('package_name') or '').strip()
        speed = (cleaned_data.get('new_package_speed') or '').strip()
        price = cleaned_data.get('new_package_price')
        create_new = cleaned_data.get('create_new_package') == '1'

        if not package_name:
            self.add_error('package_name', 'أدخل اسم الباقة.')
            return cleaned_data

        if package_id:
            package = Package.objects.filter(pk=package_id, is_active=True).first()
            if package:
                cleaned_data['package'] = package
                return self._finalize_subscription_price(cleaned_data)

        existing = self._resolve_existing_package(package_name)
        if existing:
            cleaned_data['package'] = existing
            return self._finalize_subscription_price(cleaned_data)

        if not create_new and speed and price is not None:
            create_new = True

        if create_new:
            if not speed:
                self.add_error('new_package_speed', 'أدخل سرعة الباقة الجديدة.')
            if price is None:
                self.add_error('new_package_price', 'أدخل سعر الباقة الجديدة.')
            if not self.errors:
                cleaned_data['package'] = Package.objects.create(
                    name=package_name,
                    speed=speed,
                    price=price,
                    duration_value=30,
                    duration_type='day',
                    is_active=True,
                )
            return self._finalize_subscription_price(cleaned_data)

        self.add_error(
            'package_name',
            'الباقة غير موجودة — اخترها من القائمة أو اضغط «إضافة باقة جديدة» وأكمل السرعة والسعر.',
        )
        return cleaned_data


class SubscriberForm(forms.ModelForm):
    auto_renew = forms.BooleanField(
        label='تجديد شهري تلقائياً',
        required=False,
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
    )

    class Meta:
        model = Subscriber
        fields = [
            'full_name', 'phone', 'whatsapp', 'address', 'area',
            'router_name', 'ip_address', 'mac_address',
            'pppoe_username', 'pppoe_password',
            'monthly_price', 'device', 'notes',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs=FORM_CONTROL),
            'phone': forms.TextInput(attrs=FORM_CONTROL),
            'whatsapp': forms.TextInput(attrs=FORM_CONTROL),
            'address': forms.Textarea(attrs=FORM_TEXTAREA),
            'area': forms.Select(attrs=FORM_SELECT),
            'router_name': forms.TextInput(attrs=FORM_CONTROL),
            'ip_address': forms.TextInput(attrs=FORM_CONTROL),
            'mac_address': forms.TextInput(attrs=FORM_CONTROL),
            'pppoe_username': forms.TextInput(attrs=FORM_CONTROL),
            'pppoe_password': forms.TextInput(attrs=FORM_CONTROL),
            'monthly_price': forms.NumberInput(attrs={**FORM_CONTROL, 'step': '0.01'}),
            'device': forms.Select(attrs=FORM_SELECT),
            'notes': forms.Textarea(attrs=FORM_TEXTAREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            sub = self.instance.active_subscription
            if sub:
                self.fields['auto_renew'].initial = sub.auto_renew
            else:
                del self.fields['auto_renew']


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ['name', 'notes']
        widgets = {
            'name': forms.TextInput(attrs=FORM_CONTROL),
            'notes': forms.Textarea(attrs=FORM_TEXTAREA),
        }


class HubPaymentForm(forms.Form):
    amount = forms.DecimalField(
        label='المبلغ',
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={**FORM_CONTROL, 'step': '0.01'}),
    )
    payment_date = forms.DateField(
        label='تاريخ الدفع',
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={**FORM_CONTROL, 'type': 'date'}),
    )
    method = forms.ModelChoiceField(
        label='طريقة الدفع',
        queryset=None,
        widget=forms.Select(attrs=FORM_SELECT),
    )
    description = forms.CharField(
        label='الوصف',
        required=False,
        widget=forms.Textarea(attrs={**FORM_CONTROL, 'rows': 2}),
    )
    renew_subscription = forms.BooleanField(
        label='تجديد الاشتراك مع القبض',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.finance.models import PaymentMethod
        self.fields['method'].queryset = PaymentMethod.objects.filter(is_active=True)


class HubRenewForm(forms.Form):
    package = forms.ModelChoiceField(
        label='الباقة',
        queryset=Package.objects.filter(is_active=True),
        widget=forms.Select(attrs=FORM_SELECT),
    )
    create_payment = forms.BooleanField(
        label='تسجيل دفعة بالتجديد',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
    )
    payment_method = forms.ModelChoiceField(
        label='طريقة الدفع',
        queryset=None,
        required=False,
        widget=forms.Select(attrs=FORM_SELECT),
    )
    create_debt = forms.BooleanField(
        label='ترحيل المبلغ كدين على المشترك',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
    )
    notes = forms.CharField(
        label='ملاحظات',
        required=False,
        widget=forms.Textarea(attrs={**FORM_CONTROL, 'rows': 2}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.finance.models import PaymentMethod
        self.fields['payment_method'].queryset = PaymentMethod.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('create_payment') and not cleaned.get('payment_method'):
            self.add_error('payment_method', 'اختر طريقة الدفع عند تسجيل دفعة.')
        return cleaned


class HubDebtSettleForm(forms.Form):
    debt_id = forms.IntegerField(widget=forms.HiddenInput)
    amount = forms.DecimalField(
        label='المبلغ',
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={**FORM_CONTROL, 'step': '0.01'}),
    )
    payment_date = forms.DateField(
        label='تاريخ الدفع',
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={**FORM_CONTROL, 'type': 'date'}),
    )
    method = forms.ModelChoiceField(
        label='طريقة الدفع',
        queryset=None,
        widget=forms.Select(attrs=FORM_SELECT),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.finance.models import PaymentMethod
        self.fields['method'].queryset = PaymentMethod.objects.filter(is_active=True)
