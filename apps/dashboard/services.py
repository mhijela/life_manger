from decimal import Decimal
from datetime import timedelta
from django.db import models
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.subscribers.models import Subscriber
from apps.finance.models import Debt, Cashbox
from apps.inventory.models import InventoryItem
from apps.devices.models import Device


def get_dashboard_stats():
    today = timezone.now().date()

    subscribers = Subscriber.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status='active')),
        expired=Count('id', filter=Q(status='expired')),
        debtors=Count('id', filter=Q(status='debtor')),
        suspended=Count('id', filter=Q(status='suspended')),
    )

    total_debts = Debt.objects.exclude(status='paid').aggregate(
        total=Sum('total_amount'),
        paid=Sum('paid_amount'),
    )
    remaining_debts = (total_debts['total'] or Decimal('0')) - (total_debts['paid'] or Decimal('0'))

    low_stock = InventoryItem.objects.filter(quantity__lte=models.F('min_stock')).count()

    device_alerts = Device.objects.filter(
        Q(status='maintenance') | Q(status='damaged') |
        Q(warranty_date__lte=today + timedelta(days=30), warranty_date__gte=today)
    ).count()

    return {
        'total_subscribers': subscribers['total'],
        'active_subscribers': subscribers['active'],
        'expired_subscribers': subscribers['expired'],
        'debtor_subscribers': subscribers['debtors'],
        'suspended_subscribers': subscribers['suspended'],
        'total_debts': remaining_debts,
        'daily_income': Cashbox.daily_income(today),
        'monthly_income': Cashbox.monthly_income(),
        'daily_expenses': Cashbox.daily_expenses(today),
        'monthly_expenses': Cashbox.monthly_expenses(),
        'monthly_profit': Cashbox.monthly_income() - Cashbox.monthly_expenses(),
        'cashbox_balance': Cashbox.balance(),
        'low_stock_count': low_stock,
        'device_alerts_count': device_alerts,
    }
