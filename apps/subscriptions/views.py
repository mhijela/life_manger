from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Package, Subscription
from .forms import PackageForm, SubscriptionForm, RenewForm
from .services import renew_subscription, expire_subscription, suspend_subscription


@login_required
def list_view(request):
    # العمل اليومي صار من صفحة المشتركون — القائمة القديمة تُحوَّل تلقائياً
    return redirect('subscribers:list')


@login_required
def package_list(request):
    packages = Package.objects.all()
    return render(request, 'subscriptions/packages.html', {'packages': packages})


@login_required
def package_create(request):
    if request.method == 'POST':
        form = PackageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الباقة.')
            return redirect('subscriptions:packages')
    else:
        form = PackageForm()
    return render(request, 'subscriptions/package_form.html', {'form': form, 'title': 'إضافة باقة'})


@login_required
def package_edit(request, pk):
    package = get_object_or_404(Package, pk=pk)
    if request.method == 'POST':
        form = PackageForm(request.POST, instance=package)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الباقة.')
            return redirect('subscriptions:packages')
    else:
        form = PackageForm(instance=package)
    return render(request, 'subscriptions/package_form.html', {'form': form, 'title': 'تعديل باقة'})


@login_required
def create_view(request):
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.speed = sub.package.speed
            sub.price = sub.package.price
            sub.save()
            from .models import SubscriptionHistory
            SubscriptionHistory.objects.create(subscription=sub, action='created', created_by=request.user)
            sub.subscriber.update_status()
            messages.success(request, 'تم إنشاء الاشتراك.')
            return redirect('subscribers:detail', pk=sub.subscriber_id)
    else:
        form = SubscriptionForm()
    return render(request, 'subscriptions/form.html', {'form': form, 'title': 'إضافة اشتراك'})


@login_required
def renew_view(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    if request.method == 'POST':
        form = RenewForm(request.POST)
        if form.is_valid():
            package = form.cleaned_data['package']
            renew_subscription(subscription, package=package, user=request.user, notes=form.cleaned_data.get('notes', ''))
            if form.cleaned_data.get('create_payment') and form.cleaned_data.get('payment_method'):
                from apps.finance.models import Payment
                Payment.objects.create(
                    subscriber=subscription.subscriber,
                    amount=package.price,
                    method=form.cleaned_data['payment_method'],
                    description=f'تجديد اشتراك - {package.name}',
                    created_by=request.user,
                )
            messages.success(request, 'تم تجديد الاشتراك.')
            return redirect('subscribers:detail', pk=subscription.subscriber_id)
    else:
        form = RenewForm(initial={'package': subscription.package})
    return render(request, 'subscriptions/renew.html', {'form': form, 'subscription': subscription})


@login_required
def expire_view(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    if request.method == 'POST':
        expire_subscription(subscription, user=request.user)
        messages.success(request, 'تم إنهاء الاشتراك.')
    return redirect('subscribers:detail', pk=subscription.subscriber_id)


@login_required
def suspend_view(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    if request.method == 'POST':
        suspend_subscription(subscription, user=request.user)
        messages.success(request, 'تم إيقاف الاشتراك.')
    return redirect('subscribers:detail', pk=subscription.subscriber_id)
