from django import forms
from .models import Payment, Expense, Debt, DebtPayment, PaymentMethod, ExpenseCategory

FC = {'class': 'form-control'}
FS = {'class': 'form-select'}


class PaymentForm(forms.ModelForm):
    renew_subscription = forms.BooleanField(required=False, initial=False, label='تجديد الاشتراك تلقائياً')

    class Meta:
        model = Payment
        fields = ['subscriber', 'amount', 'payment_date', 'method', 'description']
        widgets = {
            'subscriber': forms.Select(attrs=FS),
            'amount': forms.NumberInput(attrs={**FC, 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'method': forms.Select(attrs=FS),
            'description': forms.Textarea(attrs={**FC, 'rows': 2}),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'amount', 'date', 'category', 'description']
        widgets = {
            'title': forms.TextInput(attrs=FC),
            'amount': forms.NumberInput(attrs={**FC, 'step': '0.01'}),
            'date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'category': forms.Select(attrs=FS),
            'description': forms.Textarea(attrs={**FC, 'rows': 2}),
        }


class DebtForm(forms.ModelForm):
    class Meta:
        model = Debt
        fields = ['subscriber', 'total_amount', 'due_date', 'notes']
        widgets = {
            'subscriber': forms.Select(attrs=FS),
            'total_amount': forms.NumberInput(attrs={**FC, 'step': '0.01'}),
            'due_date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'notes': forms.Textarea(attrs={**FC, 'rows': 2}),
        }


class DebtPaymentForm(forms.ModelForm):
    class Meta:
        model = DebtPayment
        fields = ['amount', 'payment_date', 'method']
        widgets = {
            'amount': forms.NumberInput(attrs={**FC, 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'method': forms.Select(attrs=FS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['method'].queryset = PaymentMethod.objects.filter(is_active=True)


class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ['name', 'is_active']
        widgets = {'name': forms.TextInput(attrs=FC), 'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})}


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs=FC)}
