from django.db import models


class MessageTemplate(models.Model):
    TYPE_CHOICES = [
        ('expiry_reminder', 'تذكير انتهاء اشتراك'),
        ('debt_reminder', 'تذكير دين'),
        ('payment_confirmation', 'تأكيد دفع'),
        ('maintenance_alert', 'تنبيه صيانة'),
        ('general', 'إعلان عام'),
    ]
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
    ]

    name = models.CharField('اسم القالب', max_length=100)
    template_type = models.CharField('نوع القالب', max_length=30, choices=TYPE_CHOICES)
    channel = models.CharField('القناة', max_length=20, choices=CHANNEL_CHOICES, default='sms')
    body = models.TextField(
        'نص الرسالة',
        help_text='المتغيرات المتاحة: {name}, {amount}, {due_date}, {total_amount}, {phone}, {company}'
    )
    is_active = models.BooleanField('نشط', default=True)

    class Meta:
        verbose_name = 'قالب رسالة'
        verbose_name_plural = 'قوالب الرسائل'
        ordering = ['name']

    def __str__(self):
        return self.name

    def render(self, context):
        body = self.body
        for key, value in context.items():
            body = body.replace(f'{{{key}}}', str(value))
        return body


class MessageLog(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('sent', 'مُرسل'),
        ('failed', 'فشل'),
    ]

    template = models.ForeignKey(
        MessageTemplate, on_delete=models.SET_NULL, null=True, blank=True
    )
    recipient = models.CharField('المستلم', max_length=50)
    body = models.TextField('نص الرسالة')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField('تاريخ الإرسال', null=True, blank=True)
    error_message = models.TextField('رسالة الخطأ', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'سجل رسالة'
        verbose_name_plural = 'سجلات الرسائل'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient} - {self.get_status_display()}'
