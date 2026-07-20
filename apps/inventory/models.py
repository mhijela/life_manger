from django.db import models


class Unit(models.Model):
    name = models.CharField('اسم الوحدة', max_length=50)

    class Meta:
        verbose_name = 'وحدة قياس'
        verbose_name_plural = 'وحدات القياس'
        ordering = ['name']

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    name = models.CharField('اسم الصنف', max_length=200)
    category = models.CharField('الفئة', max_length=100, blank=True)
    quantity = models.PositiveIntegerField('الكمية', default=0)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name='الوحدة')
    purchase_price = models.DecimalField('سعر الشراء', max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField('سعر البيع', max_digits=10, decimal_places=2, default=0)
    supplier = models.CharField('المورد', max_length=200, blank=True)
    min_stock = models.PositiveIntegerField('الحد الأدنى للمخزون', default=5)
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'صنف مخزون'
        verbose_name_plural = 'أصناف المخزون'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_stock


class StockMovement(models.Model):
    TYPE_CHOICES = [
        ('in', 'إدخال'),
        ('out', 'إخراج'),
        ('adjustment', 'تعديل'),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField('نوع الحركة', max_length=20, choices=TYPE_CHOICES)
    quantity = models.PositiveIntegerField('الكمية')
    date = models.DateField('التاريخ')
    notes = models.TextField('ملاحظات', blank=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'حركة مخزون'
        verbose_name_plural = 'حركات المخزون'
        ordering = ['-date']

    def __str__(self):
        return f'{self.item} - {self.get_movement_type_display()}'

    def apply(self):
        if self.movement_type == 'in':
            self.item.quantity += self.quantity
        elif self.movement_type == 'out':
            self.item.quantity = max(0, self.item.quantity - self.quantity)
        else:
            self.item.quantity = self.quantity
        self.item.save(update_fields=['quantity', 'updated_at'])
