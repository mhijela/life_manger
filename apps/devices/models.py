from django.db import models
from django.utils import timezone


class Device(models.Model):
    TYPE_CHOICES = [
        ('router', 'راوتر'),
        ('switch', 'سويتش'),
        ('access_point', 'نقطة وصول'),
        ('server', 'سيرفر'),
        ('ups', 'UPS'),
        ('battery', 'بطارية'),
        ('solar', 'جهاز شمسي'),
    ]
    STATUS_CHOICES = [
        ('active', 'يعمل'),
        ('inactive', 'غير نشط'),
        ('maintenance', 'صيانة'),
        ('damaged', 'تالف'),
    ]

    name = models.CharField('اسم الجهاز', max_length=200)
    device_type = models.CharField('نوع الجهاز', max_length=20, choices=TYPE_CHOICES)
    ip_address = models.GenericIPAddressField('عنوان IP', null=True, blank=True)
    mac_address = models.CharField('عنوان MAC', max_length=17, blank=True)
    location = models.CharField('الموقع', max_length=200, blank=True)
    serial_number = models.CharField('الرقم التسلسلي', max_length=100, blank=True)
    username = models.CharField('اسم المستخدم', max_length=100, blank=True)
    password = models.CharField('كلمة المرور', max_length=100, blank=True)
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='active')
    purchase_date = models.DateField('تاريخ الشراء', null=True, blank=True)
    warranty_date = models.DateField('تاريخ انتهاء الضمان', null=True, blank=True)
    last_ping = models.DateTimeField('آخر ping', null=True, blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    subscriber = models.ForeignKey(
        'subscribers.Subscriber', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='devices', verbose_name='المشترك'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'جهاز'
        verbose_name_plural = 'الأجهزة'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def warranty_expiring_soon(self):
        if not self.warranty_date:
            return False
        days = (self.warranty_date - timezone.now().date()).days
        return 0 <= days <= 30


class MaintenanceNote(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='maintenance_notes')
    date = models.DateField('التاريخ')
    description = models.TextField('الوصف')
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'ملاحظة صيانة'
        verbose_name_plural = 'ملاحظات الصيانة'
        ordering = ['-date']

    def __str__(self):
        return f'{self.device} - {self.date}'
