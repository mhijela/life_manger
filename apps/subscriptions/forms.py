from django import forms
from .models import Package, Subscription

FC = {'class': 'form-control'}
FS = {'class': 'form-select'}


class PackageForm(forms.ModelForm):
    class Meta:
        model = Package
        fields = ['name', 'speed', 'price', 'duration_value', 'duration_type', 'is_active', 'notes']
        widgets = {f: forms.TextInput(attrs=FC) if f != 'notes' else forms.Textarea(attrs={**FC, 'rows': 2})
                   for f in ['name', 'speed', 'notes']}
        widgets.update({
            'price': forms.NumberInput(attrs={**FC, 'step': '0.01'}),
            'duration_value': forms.NumberInput(attrs=FC),
            'duration_type': forms.Select(attrs=FS),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        })


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['subscriber', 'package', 'start_date', 'end_date', 'auto_expiry', 'notes']
        widgets = {
            'subscriber': forms.Select(attrs=FS),
            'package': forms.Select(attrs=FS),
            'start_date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'end_date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'auto_expiry': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={**FC, 'rows': 2}),
        }


class RenewForm(forms.Form):
    package = forms.ModelChoiceField(queryset=Package.objects.filter(is_active=True), label='الباقة', widget=forms.Select(attrs=FS))
    create_payment = forms.BooleanField(required=False, initial=True, label='تسجيل دفعة')
    payment_method = forms.ModelChoiceField(
        queryset=None, required=False, label='طريقة الدفع', widget=forms.Select(attrs=FS)
    )
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={**FC, 'rows': 2}), label='ملاحظات')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.finance.models import PaymentMethod
        self.fields['payment_method'].queryset = PaymentMethod.objects.filter(is_active=True)
