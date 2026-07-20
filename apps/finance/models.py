from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class PaymentMethod(models.Model):
    name = models.CharField('اسم طريقة الدفع', max_length=50)
    is_active = models.BooleanField('نشطة', default=True)

    class Meta:
        verbose_name = 'طريقة دفع'
        verbose_name_plural = 'طرق الدفع'
        ordering = ['name']

    def __str__(self):
        return self.name


class Payment(models.Model):
    subscriber = models.ForeignKey(
        'subscribers.Subscriber', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='payments', verbose_name='المشترك'
    )
    amount = models.DecimalField('المبلغ', max_digits=12, decimal_places=2)
    payment_date = models.DateField('تاريخ الدفع', default=timezone.now)
    method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, verbose_name='طريقة الدفع')
    description = models.TextField('الوصف', blank=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دفعة'
        verbose_name_plural = 'الدفعات'
        ordering = ['-payment_date']

    def __str__(self):
        return f'{self.amount} - {self.payment_date}'


class ExpenseCategory(models.Model):
    name = models.CharField('اسم الفئة', max_length=100)
    is_default = models.BooleanField('افتراضية', default=False)

    class Meta:
        verbose_name = 'فئة مصروف'
        verbose_name_plural = 'فئات المصروفات'
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    title = models.CharField('العنوان', max_length=200)
    amount = models.DecimalField('المبلغ', max_digits=12, decimal_places=2)
    date = models.DateField('التاريخ', default=timezone.now)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, verbose_name='الفئة')
    description = models.TextField('الوصف', blank=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'مصروف'
        verbose_name_plural = 'المصروفات'
        ordering = ['-date']

    def __str__(self):
        return self.title


class Debt(models.Model):
    STATUS_CHOICES = [
        ('pending', 'معلق'),
        ('partial', 'جزئي'),
        ('paid', 'مدفوع'),
    ]

    subscriber = models.ForeignKey(
        'subscribers.Subscriber', on_delete=models.CASCADE,
        related_name='debts', verbose_name='المشترك'
    )
    total_amount = models.DecimalField('المبلغ الإجمالي', max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField('المبلغ المدفوع', max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField('تاريخ الاستحقاق')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دين'
        verbose_name_plural = 'الديون'
        ordering = ['-due_date']

    def __str__(self):
        return f'{self.subscriber} - {self.remaining_amount}'

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount

    def update_status(self):
        if self.paid_amount >= self.total_amount:
            self.status = 'paid'
        elif self.paid_amount > 0:
            self.status = 'partial'
        else:
            self.status = 'pending'
        # paid_amount is modified by callers before calling update_status,
        # so it must be persisted together with the status.
        self.save(update_fields=['paid_amount', 'status'])


class DebtPayment(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='payments', verbose_name='الدين')
    amount = models.DecimalField('المبلغ', max_digits=12, decimal_places=2)
    payment_date = models.DateField('تاريخ الدفع', default=timezone.now)
    method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, verbose_name='طريقة الدفع')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دفعة دين'
        verbose_name_plural = 'دفعات الديون'

    def __str__(self):
        return f'{self.amount} - {self.debt}'


class Cashbox:
    """Singleton helper for cashbox calculations."""

    @staticmethod
    def get_opening_balance():
        from apps.settings_app.models import SystemSettings
        return SystemSettings.load().cashbox_opening_balance

    @staticmethod
    def total_income():
        return Payment.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    @staticmethod
    def total_expenses():
        return Expense.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    @staticmethod
    def balance():
        return Cashbox.get_opening_balance() + Cashbox.total_income() - Cashbox.total_expenses()

    @staticmethod
    def daily_income(date=None):
        date = date or timezone.now().date()
        return Payment.objects.filter(payment_date=date).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    @staticmethod
    def monthly_income(year=None, month=None):
        today = timezone.now().date()
        year = year or today.year
        month = month or today.month
        return Payment.objects.filter(
            payment_date__year=year, payment_date__month=month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    @staticmethod
    def daily_expenses(date=None):
        date = date or timezone.now().date()
        return Expense.objects.filter(date=date).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    @staticmethod
    def monthly_expenses(year=None, month=None):
        today = timezone.now().date()
        year = year or today.year
        month = month or today.month
        return Expense.objects.filter(
            date__year=year, date__month=month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
