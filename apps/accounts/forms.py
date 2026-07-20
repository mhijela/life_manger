from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='البريد الإلكتروني',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'أدخل بريدك الإلكتروني'}),
    )
    password = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'أدخل كلمة المرور'}),
    )

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError('بيانات الدخول غير صحيحة.')
        return self.cleaned_data


class InitialSetupForm(forms.Form):
    first_name = forms.CharField(
        label='الاسم',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المدير', 'autofocus': True}),
    )
    email = forms.EmailField(
        label='البريد الإلكتروني',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'admin@example.com', 'dir': 'ltr'}),
    )
    password1 = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'كلمة مرور قوية'}),
        help_text='8 أحرف على الأقل',
    )
    password2 = forms.CharField(
        label='تأكيد كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'أعد كتابة كلمة المرور'}),
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('هذا البريد مستخدم مسبقاً.')
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'كلمتا المرور غير متطابقتين.')
        return cleaned

    def save(self):
        return User.objects.create_superuser(
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['first_name'],
        )