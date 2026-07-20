from django.db import models
from django.utils import timezone


class DailyTask(models.Model):
    TYPE_CHOICES = [
        ('router_installation', 'تركيب راوتر'),
        ('maintenance', 'صيانة'),
        ('repair', 'إصلاح'),
        ('other', 'مهمة أخرى'),
    ]
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغاة'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('normal', 'عادية'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]

    title = models.CharField('عنوان المهمة', max_length=200)
    task_type = models.CharField(
        'نوع المهمة', max_length=30, choices=TYPE_CHOICES, default='other'
    )
    description = models.TextField('تفاصيل المهمة', blank=True)
    scheduled_date = models.DateField('تاريخ التنفيذ', default=timezone.localdate)
    scheduled_time = models.TimeField('وقت التنفيذ', null=True, blank=True)
    status = models.CharField(
        'الحالة', max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    priority = models.CharField(
        'الأولوية', max_length=20, choices=PRIORITY_CHOICES, default='normal'
    )
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_daily_tasks',
        verbose_name='مسندة إلى',
    )
    subscriber = models.ForeignKey(
        'subscribers.Subscriber',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_tasks',
        verbose_name='المشترك',
    )
    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_tasks',
        verbose_name='الجهاز',
    )
    location = models.CharField('الموقع', max_length=250, blank=True)
    completion_notes = models.TextField('ملاحظات الإنجاز', blank=True)
    completed_at = models.DateTimeField('تاريخ الإنجاز', null=True, blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_daily_tasks',
        verbose_name='أنشأها',
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('آخر تحديث', auto_now=True)

    class Meta:
        verbose_name = 'مهمة يومية'
        verbose_name_plural = 'المهام اليومية'
        ordering = ['scheduled_date', 'scheduled_time', '-created_at']
        indexes = [
            models.Index(fields=['scheduled_date', 'status']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'completed':
            self.completed_at = None
        super().save(*args, **kwargs)
