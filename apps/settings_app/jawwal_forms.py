from django import forms


class JawwalLoginForm(forms.Form):
    username = forms.CharField(
        label='اسم المستخدم',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'user@serviceName', 'dir': 'ltr'}),
    )
    password = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
    )


class JawwalOtpForm(forms.Form):
    otp = forms.CharField(
        label='رمز OTP',
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123456', 'dir': 'ltr', 'autocomplete': 'one-time-code'}),
    )


class JawwalPaymentSmsForm(forms.Form):
    mobile = forms.CharField(
        label='رقم جوال العميل',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0599123456', 'dir': 'ltr'}),
    )
    amount = forms.DecimalField(
        label='المبلغ (₪)',
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    note = forms.CharField(
        label='ملاحظة / سبب الدفعة',
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class JawwalHarForm(forms.Form):
    har_file = forms.FileField(
        label='ملف HAR من DevTools',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.har,application/json'}),
    )
