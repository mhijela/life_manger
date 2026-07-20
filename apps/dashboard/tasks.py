from datetime import timedelta

from celery import shared_task
from django.utils import timezone


@shared_task(name='apps.dashboard.tasks.run_daily_subscription_cycle')
def run_daily_subscription_cycle():
    """Daily job: auto-renew subscriptions + carry debt, then expire the rest."""
    from apps.subscriptions.services import process_auto_renewals, expire_overdue_subscriptions

    renew_results = process_auto_renewals(send_debt_sms=True)
    expired = expire_overdue_subscriptions()
    return {
        **renew_results,
        'expired': expired,
    }


@shared_task(name='apps.dashboard.tasks.process_auto_renewals_task')
def process_auto_renewals_task():
    from apps.subscriptions.services import process_auto_renewals
    return process_auto_renewals(send_debt_sms=True)


@shared_task(name='apps.dashboard.tasks.check_subscription_expiry')
def check_subscription_expiry():
    from apps.subscriptions.services import expire_overdue_subscriptions
    count = expire_overdue_subscriptions()
    return f'Expired {count} subscriptions'


@shared_task(name='apps.dashboard.tasks.send_expiry_alerts')
def send_expiry_alerts():
    from apps.subscriptions.models import Subscription
    from apps.messages.models import MessageTemplate
    from apps.messages.services.sms_service import SMSService
    from apps.settings_app.models import SystemSettings

    settings = SystemSettings.load()
    alert_date = timezone.now().date() + timedelta(days=settings.subscription_alert_days)

    subs = Subscription.objects.filter(
        status='active', end_date=alert_date
    ).select_related('subscriber')

    template = MessageTemplate.objects.filter(
        template_type='expiry_reminder', is_active=True
    ).first()

    if not template:
        return 'No expiry template found'

    sms = SMSService()
    count = 0
    for sub in subs:
        context = {
            'name': sub.subscriber.full_name,
            'expiry_date': sub.end_date,
            'amount': sub.price,
            'company': settings.company_name,
            'phone': sub.subscriber.phone,
        }
        sms.send_template(sub.subscriber.phone, template, context)
        count += 1

    return f'Sent {count} expiry alerts'


@shared_task(name='apps.dashboard.tasks.check_low_stock')
def check_low_stock():
    from apps.inventory.models import InventoryItem
    from django.db import models

    low_items = InventoryItem.objects.filter(quantity__lte=models.F('min_stock'))
    return f'{low_items.count()} items low on stock'
