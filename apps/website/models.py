from django.db import models


class ContactRequest(models.Model):
    SERVICE_CHOICES = [
        ('websites', 'تصميم وتطوير المواقع'),
        ('custom_software', 'الأنظمة والبرامج المخصصة'),
        ('networks', 'شبكات الإنترنت'),
        ('cloud', 'الخوادم والحوسبة السحابية'),
        ('support', 'الدعم الفني والصيانة'),
        ('security', 'الأمن السيبراني'),
        ('marketing', 'التسويق الرقمي'),
        ('consulting', 'الاستشارات التقنية'),
        ('other', 'أخرى'),
    ]

    name = models.CharField('الاسم', max_length=120)
    phone = models.CharField('رقم الهاتف', max_length=30)
    email = models.EmailField('البريد الإلكتروني', blank=True)
    service = models.CharField('نوع الخدمة', max_length=40, choices=SERVICE_CHOICES)
    message = models.TextField('تفاصيل الطلب')
    created_at = models.DateTimeField('تاريخ الإرسال', auto_now_add=True)
    is_handled = models.BooleanField('تمت المتابعة', default=False)

    class Meta:
        verbose_name = 'طلب تواصل'
        verbose_name_plural = 'طلبات التواصل'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.get_service_display()}'
