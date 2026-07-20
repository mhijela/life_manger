from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import User, UserProfile


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


class AccountProfileForm(forms.Form):
    use_required_attribute = False

    first_name = forms.CharField(
        label='الاسم الأول',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        label='اسم العائلة',
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        label='البريد الإلكتروني',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
    )
    phone = forms.CharField(
        label='رقم الجوال',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr', 'placeholder': '05xxxxxxxx'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if not args:
            profile = getattr(user, 'profile', None)
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            self.fields['phone'].initial = profile.phone if profile else ''

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('هذا البريد مستخدم من حساب آخر.')
        return email

    def save(self):
        user = self.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data['email']
        user.save(update_fields=['first_name', 'last_name', 'email'])
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone = self.cleaned_data.get('phone', '')
        profile.save(update_fields=['phone'])
        return user


class AccountPasswordForm(forms.Form):
    # يمنع required في HTML من تعطيل إرسال تبويبات أخرى (نسخ احتياطي…)
    use_required_attribute = False

    current_password = forms.CharField(
        label='كلمة المرور الحالية',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}),
    )
    new_password1 = forms.CharField(
        label='كلمة المرور الجديدة',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        help_text='8 أحرف على الأقل',
    )
    new_password2 = forms.CharField(
        label='تأكيد كلمة المرور الجديدة',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data['current_password']
        if not self.user.check_password(password):
            raise forms.ValidationError('كلمة المرور الحالية غير صحيحة.')
        return password

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if password:
            validate_password(password, self.user)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password1')
        p2 = cleaned.get('new_password2')
        if p1 and p2 and p1 != p2:
            self.add_error('new_password2', 'كلمتا المرور غير متطابقتين.')
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data['new_password1'])
        self.user.save(update_fields=['password'])
        return self.user
