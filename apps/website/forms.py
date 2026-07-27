from django import forms

from .models import ContactRequest


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactRequest
        fields = ('name', 'phone', 'email', 'service', 'message')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'zt-input',
                'placeholder': 'الاسم الكامل',
                'autocomplete': 'name',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'zt-input',
                'placeholder': '05xxxxxxxx',
                'autocomplete': 'tel',
                'dir': 'ltr',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'zt-input',
                'placeholder': 'email@example.com',
                'autocomplete': 'email',
                'dir': 'ltr',
            }),
            'service': forms.Select(attrs={'class': 'zt-input'}),
            'message': forms.Textarea(attrs={
                'class': 'zt-input',
                'rows': 4,
                'placeholder': 'أخبرنا عن مشروعك أو احتياجك...',
            }),
        }
        labels = {
            'name': 'الاسم',
            'phone': 'رقم الهاتف',
            'email': 'البريد الإلكتروني',
            'service': 'نوع الخدمة',
            'message': 'تفاصيل الطلب',
        }
