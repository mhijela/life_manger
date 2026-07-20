from django.db import models
from django.utils import timezone


class Area(models.Model):
    name = models.CharField('اسم المنطقة', max_length=100)
    latitude = models.DecimalField('خط العرض', max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField('خط الطول', max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField('ملاحظات', blank=True)

    class Meta:
        verbose_name = 'منطقة'
        verbose_name_plural = 'المناطق'
        ordering = ['name']

    def __str__(self):
        return self.name


class Subscriber(models.Model):
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('suspended', 'موقوف'),
        ('debtor', 'مدين'),
    ]

    full_name = models.CharField('الاسم الكامل', max_length=200)
    phone = models.CharField('رقم الهاتف', max_length=20)
    whatsapp = models.CharField('رقم واتساب', max_length=20, blank=True)
    address = models.TextField('العنوان', blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المنطقة')
    router_name = models.CharField('اسم الراوتر/الجهاز', max_length=100, blank=True)
    ip_address = models.GenericIPAddressField('عنوان IP', null=True, blank=True)
    mac_address = models.CharField('عنوان MAC', max_length=17, blank=True)
    pppoe_username = models.CharField('اسم مستخدم PPPoE', max_length=100, blank=True)
    pppoe_password = models.CharField('كلمة مرور PPPoE', max_length=100, blank=True)
    monthly_price = models.DecimalField('السعر الشهري', max_digits=10, decimal_places=2, default=0)
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='expired')
    is_suspended = models.BooleanField('موقوف يدوياً', default=False)
    notes = models.TextField('ملاحظات', blank=True)
    device = models.ForeignKey(
        'devices.Device', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='linked_subscribers', verbose_name='الجهاز المرتبط'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'مشترك'
        verbose_name_plural = 'المشتركون'
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name

    @property
    def active_subscription(self):
        return self.subscriptions.filter(status='active').first()

    def has_unpaid_debt(self):
        return self.debts.exclude(status='paid').exists()

    def update_status(self, save=True):
        if self.is_suspended:
            self.status = 'suspended'
        elif self.has_unpaid_debt():
            self.status = 'debtor'
        else:
            sub = self.active_subscription
            if sub and sub.end_date >= timezone.now().date():
                self.status = 'active'
            else:
                self.status = 'expired'
        if save:
            self.save(update_fields=['status', 'updated_at'])
