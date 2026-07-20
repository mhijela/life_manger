from django.db import models


class AssetCategory(models.Model):
    name = models.CharField('اسم الفئة', max_length=100)

    class Meta:
        verbose_name = 'فئة أصل'
        verbose_name_plural = 'فئات الأصول'
        ordering = ['name']

    def __str__(self):
        return self.name


class Asset(models.Model):
    STATUS_CHOICES = [
        ('available', 'متاح'),
        ('assigned', 'مُسلّم'),
        ('returned', 'مُسترجع'),
        ('damaged', 'تالف'),
    ]

    name = models.CharField('اسم الأصل', max_length=200)
    serial_number = models.CharField('الرقم التسلسلي', max_length=100, blank=True)
    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT, verbose_name='الفئة')
    assigned_to = models.ForeignKey(
        'subscribers.Subscriber', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assets', verbose_name='مُسلّم إلى'
    )
    assignment_date = models.DateField('تاريخ التسليم', null=True, blank=True)
    return_date = models.DateField('تاريخ الإرجاع', null=True, blank=True)
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='available')
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'أصل'
        verbose_name_plural = 'الأصول'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class AssetHistory(models.Model):
    ACTION_CHOICES = [
        ('assigned', 'تسليم'),
        ('returned', 'إرجاع'),
        ('damaged', 'تلف'),
        ('repaired', 'إصلاح'),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='history')
    action = models.CharField('الإجراء', max_length=20, choices=ACTION_CHOICES)
    date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField('ملاحظات', blank=True)
    subscriber = models.ForeignKey(
        'subscribers.Subscriber', on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = 'سجل أصل'
        verbose_name_plural = 'سجلات الأصول'
        ordering = ['-date']

    def __str__(self):
        return f'{self.asset} - {self.get_action_display()}'
