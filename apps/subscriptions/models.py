from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils import timezone


class Package(models.Model):
    DURATION_TYPE_CHOICES = [
        ('day', 'يوم'),
        ('month', 'شهر'),
        ('year', 'سنة'),
    ]

    name = models.CharField('اسم الباقة', max_length=100)
    speed = models.CharField('السرعة', max_length=50)
    price = models.DecimalField('السعر', max_digits=10, decimal_places=2)
    duration_value = models.PositiveIntegerField('مدة الاشتراك', default=1)
    duration_type = models.CharField('نوع المدة', max_length=10, choices=DURATION_TYPE_CHOICES, default='month')
    is_active = models.BooleanField('نشطة', default=True)
    notes = models.TextField('ملاحظات', blank=True)

    class Meta:
        verbose_name = 'باقة'
        verbose_name_plural = 'الباقات'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} - {self.speed}'

    def calculate_end_date(self, start_date):
        if self.duration_type == 'day':
            return start_date + timedelta(days=self.duration_value)
        elif self.duration_type == 'month':
            return start_date + relativedelta(months=self.duration_value)
        return start_date + relativedelta(years=self.duration_value)


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('suspended', 'موقوف'),
    ]

    subscriber = models.ForeignKey(
        'subscribers.Subscriber', on_delete=models.CASCADE,
        related_name='subscriptions', verbose_name='المشترك'
    )
    package = models.ForeignKey(Package, on_delete=models.PROTECT, verbose_name='الباقة')
    speed = models.CharField('السرعة', max_length=50)
    price = models.DecimalField('السعر', max_digits=10, decimal_places=2)
    start_date = models.DateField('تاريخ البداية')
    end_date = models.DateField('تاريخ النهاية')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='active')
    auto_expiry = models.BooleanField('انتهاء تلقائي', default=True)
    auto_renew = models.BooleanField('تجديد شهري تلقائياً', default=True)
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'اشتراك'
        verbose_name_plural = 'الاشتراكات'
        ordering = ['-end_date']

    def __str__(self):
        return f'{self.subscriber} - {self.package.name}'

    def is_expired(self):
        return self.end_date < timezone.localdate()

    def days_remaining(self):
        delta = self.end_date - timezone.localdate()
        return max(delta.days, 0)


class SubscriptionHistory(models.Model):
    ACTION_CHOICES = [
        ('created', 'إنشاء'),
        ('renewed', 'تجديد'),
        ('expired', 'انتهاء'),
        ('suspended', 'إيقاف'),
        ('reactivated', 'تفعيل'),
    ]

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE,
        related_name='history', verbose_name='الاشتراك'
    )
    action = models.CharField('الإجراء', max_length=20, choices=ACTION_CHOICES)
    date = models.DateTimeField('التاريخ', auto_now_add=True)
    notes = models.TextField('ملاحظات', blank=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = 'سجل الاشتراك'
        verbose_name_plural = 'سجلات الاشتراكات'
        ordering = ['-date']

    def __str__(self):
        return f'{self.subscription} - {self.get_action_display()}'
