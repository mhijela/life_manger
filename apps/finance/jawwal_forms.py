from django import forms


class JawwalPaymentRequestForm(forms.Form):
    mobile = forms.CharField(
        label='رقم جوال الزبون',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0599123456', 'dir': 'ltr'}),
    )
    amount = forms.DecimalField(
        label='المبلغ (₪)',
        min_value=0.01,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )


class JawwalVerificationForm(forms.Form):
    verification_code = forms.CharField(
        label='رمز التحقق',
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345',
            'dir': 'ltr',
            'autocomplete': 'one-time-code',
        }),
        help_text='الرمز المرسل لإتمام طلب الدفعة',
    )
