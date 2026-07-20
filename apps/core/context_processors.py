from datetime import timedelta

from django.db.models import F, Q, Sum
from django.urls import reverse
from django.utils import timezone


def topbar_notifications(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'topbar_notifications': [], 'topbar_notifications_count': 0}

    today = timezone.localdate()
    items = []

    try:
        from apps.settings_app.models import SystemSettings
        from apps.subscriptions.models import Subscription
        from apps.inventory.models import InventoryItem
        from apps.devices.models import Device
        from apps.finance.models import Debt
        from apps.daily_tasks.models import DailyTask

        alert_days = SystemSettings.load().subscription_alert_days or 3

        expired_count = Subscription.objects.filter(
            Q(status='expired') | Q(status='active', end_date__lt=today)
        ).values('subscriber_id').distinct().count()
        if expired_count:
            items.append({
                'title': f'{expired_count} اشتراك منتهي',
                'subtitle': 'يحتاجون تجديداً أو متابعة',
                'icon': 'bi-x-circle',
                'tone': 'danger',
                'url': reverse('subscribers:list') + '?subscription_state=expired',
            })

        expiring_count = Subscription.objects.filter(
            status='active',
            end_date__gte=today,
            end_date__lte=today + timedelta(days=alert_days),
        ).count()
        if expiring_count:
            items.append({
                'title': f'{expiring_count} اشتراك ينتهي قريباً',
                'subtitle': f'خلال {alert_days} أيام',
                'icon': 'bi-clock-history',
                'tone': 'warning',
                'url': reverse('subscribers:list') + '?subscription_state=expiring_soon',
            })

        debts = Debt.objects.exclude(status='paid').aggregate(
            total=Sum('total_amount'),
            paid=Sum('paid_amount'),
        )
        remaining = (debts['total'] or 0) - (debts['paid'] or 0)
        open_debts = Debt.objects.exclude(status='paid').count()
        if open_debts:
            items.append({
                'title': f'{open_debts} دين مفتوح',
                'subtitle': f'المتبقي تقريباً {remaining:.0f}',
                'icon': 'bi-wallet2',
                'tone': 'warning',
                'url': reverse('finance:debts'),
            })

        low_stock = InventoryItem.objects.filter(quantity__lte=F('min_stock')).count()
        if low_stock:
            items.append({
                'title': f'{low_stock} صنف مخزون منخفض',
                'subtitle': 'الكمية عند الحد الأدنى أو أقل',
                'icon': 'bi-box-seam',
                'tone': 'danger',
                'url': reverse('inventory:list'),
            })

        device_alerts = Device.objects.filter(
            status__in=['maintenance', 'damaged']
        ).count()
        if device_alerts:
            items.append({
                'title': f'{device_alerts} تنبيه أجهزة',
                'subtitle': 'صيانة أو تالف',
                'icon': 'bi-router',
                'tone': 'warning',
                'url': reverse('devices:list'),
            })

        pending_tasks = DailyTask.objects.filter(
            scheduled_date=today,
            status__in=['pending', 'in_progress'],
        ).count()
        if pending_tasks:
            items.append({
                'title': f'{pending_tasks} مهمة لليوم',
                'subtitle': 'قيد الانتظار أو التنفيذ',
                'icon': 'bi-list-check',
                'tone': 'primary',
                'url': reverse('daily_tasks:list') + f'?date={today.isoformat()}',
            })
    except Exception:
        items = []

    return {
        'topbar_notifications': items[:8],
        'topbar_notifications_count': len(items),
    }
