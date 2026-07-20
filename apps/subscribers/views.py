from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import OuterRef, Prefetch, Q, Subquery
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.core.mixins import paginate_queryset
from apps.finance.models import Payment, Debt, DebtPayment, PaymentMethod
from apps.subscriptions.models import Package, Subscription
from apps.subscriptions.services import (
    create_subscriber_subscription,
    create_renewal_debt,
    renew_subscription,
)
from .models import Subscriber, Area
from .forms import (
    SubscriberForm,
    SubscriberCreateForm,
    AreaForm,
    HubPaymentForm,
    HubRenewForm,
    HubDebtSettleForm,
)


def _current_subscription(subscriber):
    return (
        subscriber.active_subscription
        or subscriber.subscriptions.order_by('-end_date').first()
    )


def _open_debts(subscriber):
    return subscriber.debts.exclude(status='paid').order_by('due_date')


@login_required
def list_view(request):
    latest_subscription = Subscription.objects.filter(
        subscriber=OuterRef('pk')
    ).order_by('-end_date')
    queryset = Subscriber.objects.select_related('area', 'device').annotate(
        latest_subscription_status=Subquery(latest_subscription.values('status')[:1]),
        latest_subscription_end_date=Subquery(latest_subscription.values('end_date')[:1]),
        latest_subscription_auto_renew=Subquery(latest_subscription.values('auto_renew')[:1]),
    ).prefetch_related(
        Prefetch(
            'subscriptions',
            queryset=Subscription.objects.select_related('package').order_by('-end_date'),
            to_attr='subscription_list',
        )
    )
    subscription_state = request.GET.get('subscription_state', '')
    search = request.GET.get('q', '')
    area_id = request.GET.get('area', '')
    per_page_options = (10, 20, 50, 100)
    requested_per_page = request.GET.get('per_page')
    if requested_per_page and requested_per_page.isdigit():
        requested_per_page = int(requested_per_page)
        if requested_per_page in per_page_options:
            request.session['subscribers_per_page'] = requested_per_page
    per_page = request.session.get('subscribers_per_page')
    if per_page not in per_page_options:
        per_page = 20

    if subscription_state in ('None', 'null'):
        subscription_state = ''
    if not str(area_id).isdigit():
        area_id = ''

    today = timezone.localdate()
    if subscription_state == 'active':
        queryset = queryset.filter(
            latest_subscription_status='active',
            latest_subscription_end_date__gte=today,
        )
    elif subscription_state == 'expiring_soon':
        queryset = queryset.filter(
            latest_subscription_status='active',
            latest_subscription_end_date__range=(today, today + timedelta(days=7)),
        )
    elif subscription_state == 'expired':
        queryset = queryset.filter(
            Q(latest_subscription_status='expired')
            | Q(latest_subscription_status='active', latest_subscription_end_date__lt=today)
        )
    elif subscription_state == 'suspended':
        queryset = queryset.filter(latest_subscription_status='suspended')
    elif subscription_state == 'auto_renew':
        queryset = queryset.filter(latest_subscription_auto_renew=True)
    elif subscription_state == 'manual_renew':
        queryset = queryset.filter(latest_subscription_auto_renew=False)
    elif subscription_state == 'no_subscription':
        queryset = queryset.filter(latest_subscription_status__isnull=True)

    if area_id:
        queryset = queryset.filter(area_id=area_id)
    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search) | Q(phone__icontains=search) |
            Q(ip_address__icontains=search) | Q(mac_address__icontains=search)
        )

    page_obj = paginate_queryset(request, queryset, per_page=per_page)
    return render(request, 'subscribers/list.html', {
        'page_obj': page_obj,
        'subscription_state_choices': [
            ('active', 'ساري'),
            ('expiring_soon', 'ينتهي خلال 7 أيام'),
            ('expired', 'منتهي'),
            ('suspended', 'موقوف'),
            ('auto_renew', 'تجديد تلقائي'),
            ('manual_renew', 'تجديد يدوي'),
            ('no_subscription', 'بدون اشتراك'),
        ],
        'areas': Area.objects.all(),
        'current_subscription_state': subscription_state,
        'search': search,
        'current_area': area_id,
        'per_page': per_page,
        'per_page_options': per_page_options,
        'today': today,
    })


@login_required
def detail_view(request, pk):
    subscriber = get_object_or_404(
        Subscriber.objects.select_related('area', 'device'), pk=pk
    )
    current_sub = _current_subscription(subscriber)
    open_debts = list(_open_debts(subscriber))
    debt_remaining = sum((d.remaining_amount for d in open_debts), Decimal('0'))
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    pay_form = HubPaymentForm(initial={
        'amount': subscriber.monthly_price or (current_sub.price if current_sub else None),
    })
    renew_form = HubRenewForm(initial={
        'package': current_sub.package_id if current_sub else None,
    })
    if current_sub:
        renew_form.fields['package'].queryset = Package.objects.filter(
            Q(is_active=True) | Q(pk=current_sub.package_id)
        ).distinct()
    settle_form = HubDebtSettleForm()
    return render(request, 'subscribers/detail.html', {
        'subscriber': subscriber,
        'current_subscription': current_sub,
        'subscriptions': subscriber.subscriptions.select_related('package').order_by('-end_date'),
        'payments': subscriber.payments.select_related('method').order_by('-payment_date')[:20],
        'debts': subscriber.debts.order_by('-due_date'),
        'open_debts': open_debts,
        'debt_remaining': debt_remaining,
        'assets': subscriber.assets.select_related('category'),
        'payment_methods': payment_methods,
        'has_payment_methods': payment_methods.exists(),
        'pay_form': pay_form,
        'renew_form': renew_form,
        'settle_form': settle_form,
        'today': timezone.localdate(),
    })


@login_required
@require_POST
def hub_pay(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    form = HubPaymentForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'تعذر تسجيل القبض. تحقق من البيانات.')
        return redirect('subscribers:detail', pk=pk)

    data = form.cleaned_data
    Payment.objects.create(
        subscriber=subscriber,
        amount=data['amount'],
        payment_date=data['payment_date'],
        method=data['method'],
        description=data.get('description') or 'قبض من صفحة المشترك',
        created_by=request.user,
    )

    if data.get('renew_subscription'):
        sub = _current_subscription(subscriber)
        if sub:
            renew_subscription(sub, package=sub.package, user=request.user, notes='تجديد مع القبض')
            messages.success(request, 'تم تسجيل القبض وتجديد الاشتراك.')
        else:
            messages.success(request, 'تم تسجيل القبض. لا يوجد اشتراك للتجديد.')
    else:
        messages.success(request, 'تم تسجيل القبض.')

    subscriber.update_status()
    return redirect('subscribers:detail', pk=pk)


@login_required
@require_POST
def hub_renew(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    sub = _current_subscription(subscriber)
    if not sub:
        messages.error(request, 'لا يوجد اشتراك يمكن تجديده.')
        return redirect('subscribers:detail', pk=pk)

    form = HubRenewForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'تعذر تجديد الاشتراك. تحقق من البيانات.')
        return redirect('subscribers:detail', pk=pk)

    data = form.cleaned_data
    package = data['package']
    renew_subscription(
        sub,
        package=package,
        user=request.user,
        notes=data.get('notes') or '',
    )

    if data.get('create_debt'):
        create_renewal_debt(
            subscriber,
            sub.price,
            due_date=sub.start_date,
            subscription=sub,
            notes=f'تجديد اشتراك — {sub.speed} — {sub.start_date} إلى {sub.end_date}',
        )

    if data.get('create_payment') and data.get('payment_method'):
        Payment.objects.create(
            subscriber=subscriber,
            amount=sub.price,
            method=data['payment_method'],
            description=f'تجديد اشتراك - {package.name}',
            created_by=request.user,
        )

    messages.success(request, 'تم تجديد الاشتراك.')
    return redirect('subscribers:detail', pk=pk)


@login_required
@require_POST
def hub_settle_debt(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    form = HubDebtSettleForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'تعذر تسديد الدين. تحقق من البيانات.')
        return redirect('subscribers:detail', pk=pk)

    data = form.cleaned_data
    debt = get_object_or_404(Debt, pk=data['debt_id'], subscriber=subscriber)
    if debt.status == 'paid':
        messages.warning(request, 'هذا الدين مسدد بالكامل.')
        return redirect('subscribers:detail', pk=pk)

    amount = data['amount']
    if amount > debt.remaining_amount:
        messages.error(request, 'المبلغ أكبر من المتبقي على الدين.')
        return redirect('subscribers:detail', pk=pk)

    DebtPayment.objects.create(
        debt=debt,
        amount=amount,
        payment_date=data['payment_date'],
        method=data['method'],
    )
    debt.paid_amount += amount
    debt.update_status()
    subscriber.update_status()
    Payment.objects.create(
        subscriber=subscriber,
        amount=amount,
        payment_date=data['payment_date'],
        method=data['method'],
        description=f'سداد دين مستحق بتاريخ {debt.due_date}',
        created_by=request.user,
    )
    messages.success(request, 'تم تسجيل تسديد الدين.')
    return redirect('subscribers:detail', pk=pk)

@login_required
def package_search(request):
    query = request.GET.get('q', '').strip()
    packages = Package.objects.filter(is_active=True)
    if query:
        packages = packages.filter(Q(name__icontains=query) | Q(speed__icontains=query))
    packages = packages.order_by('name')[:12]
    exact_match = bool(
        query and packages.filter(name__iexact=query).exists()
    )
    return JsonResponse({
        'results': [
            {
                'id': pkg.id,
                'name': pkg.name,
                'speed': pkg.speed,
                'price': str(pkg.price),
                'label': f'{pkg.name} — {pkg.speed} — {pkg.price}',
            }
            for pkg in packages
        ],
        'query': query,
        'exact_match': exact_match,
    })


@login_required
def create_view(request):
    if request.method == 'POST':
        form = SubscriberCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            package = data['package']
            subscription_price = data['subscription_price']
            subscriber = Subscriber.objects.create(
                full_name=data['full_name'],
                phone=data['phone'],
                pppoe_username=data.get('pppoe_username', ''),
                pppoe_password=data.get('pppoe_password', ''),
                monthly_price=subscription_price,
            )
            create_subscriber_subscription(
                subscriber,
                package=package,
                start_date=data['subscription_start_date'],
                auto_renew=data['auto_renew'],
                price=subscription_price,
                user=request.user,
            )
            if data.get('create_new_package') == '1':
                messages.info(request, f'تم إنشاء الباقة «{package.name}» وربطها بالمشترك.')
            messages.success(request, f'تم إضافة المشترك {subscriber.full_name} بنجاح.')
            return redirect('subscribers:detail', pk=subscriber.pk)
    else:
        form = SubscriberCreateForm()
    return render(request, 'subscribers/create.html', {
        'form': form,
        'title': 'إضافة مشترك',
    })


@login_required
def edit_view(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    if request.method == 'POST':
        form = SubscriberForm(request.POST, instance=subscriber)
        if form.is_valid():
            auto_renew = form.cleaned_data.pop('auto_renew', None)
            form.save()
            sub = subscriber.active_subscription
            if sub is not None and auto_renew is not None:
                sub.auto_renew = auto_renew
                sub.save(update_fields=['auto_renew', 'updated_at'])
            subscriber.update_status()
            messages.success(request, 'تم تحديث بيانات المشترك.')
            return redirect('subscribers:detail', pk=pk)
    else:
        form = SubscriberForm(instance=subscriber)
    return render(request, 'subscribers/form.html', {'form': form, 'title': 'تعديل مشترك', 'subscriber': subscriber})


@login_required
def delete_view(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    if request.method == 'POST':
        name = subscriber.full_name
        subscriber.delete()
        messages.success(request, f'تم حذف المشترك {name}.')
        return redirect('subscribers:list')
    return render(request, 'subscribers/delete.html', {'subscriber': subscriber})


@login_required
def suspend_view(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    if request.method == 'POST':
        subscriber.is_suspended = True
        subscriber.status = 'suspended'
        subscriber.save()
        sub = subscriber.active_subscription
        if sub:
            from apps.subscriptions.services import suspend_subscription
            suspend_subscription(sub, user=request.user)
        messages.success(request, 'تم إيقاف المشترك.')
        return redirect('subscribers:detail', pk=pk)
    return redirect('subscribers:detail', pk=pk)


@login_required
def activate_view(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    if request.method == 'POST':
        subscriber.is_suspended = False
        subscriber.update_status()
        messages.success(request, 'تم تفعيل المشترك.')
        return redirect('subscribers:detail', pk=pk)
    return redirect('subscribers:detail', pk=pk)
