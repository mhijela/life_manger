from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from apps.core.mixins import paginate_queryset
from .models import Payment, Expense, Debt, Cashbox
from .forms import PaymentForm, ExpenseForm, DebtForm, DebtPaymentForm
from .services import (
    send_debt_reminder_sms,
    get_debt_sms_template,
    bulk_send_debt_reminders,
    send_sms_to_all_debtors,
    get_debtor_subscribers,
    _format_bulk_sms_result,
)
from apps.messages.services.sms_service import SMSService


@login_required
def index(request):
    today = timezone.now().date()
    return render(request, 'finance/index.html', {
        'balance': Cashbox.balance(),
        'daily_income': Cashbox.daily_income(today),
        'monthly_income': Cashbox.monthly_income(),
        'daily_expenses': Cashbox.daily_expenses(today),
        'monthly_expenses': Cashbox.monthly_expenses(),
        'monthly_profit': Cashbox.monthly_income() - Cashbox.monthly_expenses(),
        'recent_payments': Payment.objects.select_related('subscriber', 'method')[:10],
        'recent_expenses': Expense.objects.select_related('category')[:10],
    })


@login_required
def payment_list(request):
    page_obj = paginate_queryset(request, Payment.objects.select_related('subscriber', 'method'))
    return render(request, 'finance/payments.html', {'page_obj': page_obj})


@login_required
def payment_create(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.save()
            if form.cleaned_data.get('renew_subscription') and payment.subscriber:
                sub = payment.subscriber.active_subscription
                if sub:
                    from apps.subscriptions.services import renew_subscription
                    renew_subscription(sub, user=request.user)
                else:
                    from apps.subscriptions.models import Package
                    from apps.subscriptions.services import create_subscription
                    pkg = Package.objects.filter(is_active=True).first()
                    if pkg:
                        create_subscription(payment.subscriber, pkg, user=request.user)
            if payment.subscriber:
                payment.subscriber.update_status()
            messages.success(request, 'تم تسجيل الدفعة.')
            return redirect('finance:payments')
    else:
        form = PaymentForm()
    return render(request, 'finance/payment_form.html', {'form': form, 'title': 'تسجيل دفعة'})


@login_required
def expense_list(request):
    page_obj = paginate_queryset(request, Expense.objects.select_related('category'))
    return render(request, 'finance/expenses.html', {'page_obj': page_obj})


@login_required
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            messages.success(request, 'تم تسجيل المصروف.')
            return redirect('finance:expenses')
    else:
        form = ExpenseForm()
    return render(request, 'finance/expense_form.html', {'form': form, 'title': 'تسجيل مصروف'})


@login_required
def debt_list(request):
    page_obj = paginate_queryset(request, Debt.objects.select_related('subscriber'))
    debtors_count = get_debtor_subscribers().count()
    return render(request, 'finance/debts.html', {
        'page_obj': page_obj,
        'sms_configured': SMSService().is_configured(),
        'debt_sms_template': get_debt_sms_template(),
        'debtors_count': debtors_count,
    })


@login_required
def debt_create(request):
    if request.method == 'POST':
        form = DebtForm(request.POST)
        if form.is_valid():
            debt = form.save()
            debt.subscriber.update_status()
            messages.success(request, 'تم تسجيل الدين.')
            return redirect('finance:debts')
    else:
        form = DebtForm()
    return render(request, 'finance/debt_form.html', {'form': form, 'title': 'تسجيل دين'})


@login_required
def debt_bulk_action(request):
    if request.method != 'POST':
        return redirect('finance:debts')

    action = request.POST.get('action')
    ids = request.POST.getlist('ids')

    if not ids:
        messages.warning(request, 'لم يتم تحديد أي ديون.')
        return redirect('finance:debts')

    debts = Debt.objects.filter(pk__in=ids).select_related('subscriber')

    if action == 'send_sms':
        result = bulk_send_debt_reminders(debts)
        level, msg = _format_bulk_sms_result(result)
        if level == 'error':
            messages.error(request, msg)
        else:
            messages.success(request, msg)
            if result['errors']:
                messages.warning(request, '؛ '.join(result['errors']))
    elif action == 'delete':
        if not request.POST.get('confirm_delete'):
            messages.error(request, 'تأكيد الحذف مطلوب.')
            return redirect('finance:debts')
        subscriber_ids = set(debts.values_list('subscriber_id', flat=True))
        count = debts.count()
        debts.delete()
        from apps.subscribers.models import Subscriber
        for sid in subscriber_ids:
            Subscriber.objects.get(pk=sid).update_status()
        messages.success(request, f'تم حذف {count} دين.')
    else:
        messages.error(request, 'إجراء غير معروف.')

    return redirect('finance:debts')


@login_required
def debt_send_all_sms(request):
    if request.method != 'POST':
        return redirect('finance:debts')

    debtors_count = get_debtor_subscribers().count()
    if not debtors_count:
        messages.warning(request, 'لا يوجد مديونون حالياً.')
        return redirect('finance:debts')

    result = send_sms_to_all_debtors()
    level, msg = _format_bulk_sms_result(result)
    if level == 'error':
        messages.error(request, msg)
    else:
        messages.success(request, msg)
        if result['errors']:
            messages.warning(request, '؛ '.join(result['errors']))

    return redirect('finance:debts')


@login_required
def debt_send_sms(request, pk):
    if request.method != 'POST':
        return redirect('finance:debts')

    debt = get_object_or_404(Debt.objects.select_related('subscriber'), pk=pk)

    if debt.status == 'paid':
        messages.warning(request, 'لا يمكن إرسال تذكير لدين مدفوع بالكامل.')
        return redirect('finance:debts')

    log, error = send_debt_reminder_sms(debt)
    if error:
        messages.error(request, error)
    elif log.status == 'sent':
        messages.success(request, f'تم إرسال SMS إلى {debt.subscriber.full_name}.')
    else:
        messages.error(request, log.error_message or 'فشل إرسال الرسالة.')

    return redirect('finance:debts')


@login_required
def debt_pay(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    if request.method == 'POST':
        form = DebtPaymentForm(request.POST)
        if form.is_valid():
            dp = form.save(commit=False)
            dp.debt = debt
            dp.save()
            debt.paid_amount += dp.amount
            debt.update_status()
            debt.subscriber.update_status()
            # تسجيل الدفعة في سجل دفعات المشترك (وإيرادات الصندوق)
            Payment.objects.create(
                subscriber=debt.subscriber,
                amount=dp.amount,
                payment_date=dp.payment_date,
                method=dp.method,
                description=f'سداد دين مستحق بتاريخ {debt.due_date}',
                created_by=request.user,
            )
            messages.success(request, 'تم تسجيل دفعة الدين.')
            return redirect('finance:debts')
    else:
        form = DebtPaymentForm(initial={'amount': debt.remaining_amount})
    return render(request, 'finance/debt_pay.html', {
        'form': form,
        'debt': debt,
        'has_payment_methods': form.fields['method'].queryset.exists(),
    })
