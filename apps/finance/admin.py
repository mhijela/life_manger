from django.contrib import admin
from .models import PaymentMethod, Payment, ExpenseCategory, Expense, Debt, DebtPayment


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'amount', 'payment_date', 'method')
    list_filter = ('payment_date', 'method')
    search_fields = ('subscriber__full_name',)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'date', 'category')
    list_filter = ('date', 'category')


class DebtPaymentInline(admin.TabularInline):
    model = DebtPayment
    extra = 0


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'total_amount', 'paid_amount', 'status', 'due_date')
    list_filter = ('status',)
    inlines = [DebtPaymentInline]
