from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import models
from datetime import timedelta
from django.utils import timezone
from .services import get_dashboard_stats
from apps.subscriptions.models import Subscription
from apps.inventory.models import InventoryItem
from apps.devices.models import Device


@login_required
def index(request):
    stats = get_dashboard_stats()
    alert_days = 3
    try:
        from apps.settings_app.models import SystemSettings
        alert_days = SystemSettings.load().subscription_alert_days
    except Exception:
        pass

    today = timezone.localdate()
    expiring_soon = Subscription.objects.filter(
        status='active',
        end_date__lte=today + timedelta(days=alert_days),
        end_date__gte=today,
    ).select_related('subscriber', 'package')[:10]

    low_stock_items = InventoryItem.objects.filter(
        quantity__lte=models.F('min_stock')
    )[:10]

    device_alerts = Device.objects.filter(
        status__in=['maintenance', 'damaged']
    )[:10]

    return render(request, 'dashboard/index.html', {
        'stats': stats,
        'expiring_soon': expiring_soon,
        'low_stock_items': low_stock_items,
        'device_alerts': device_alerts,
    })
