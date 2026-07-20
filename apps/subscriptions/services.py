from datetime import timedelta
from django.utils import timezone
from apps.subscriptions.models import Subscription, SubscriptionHistory, Package

SUBSCRIPTION_DAYS = 30
CUSTOM_PACKAGE_NAME = 'مخصص'


def get_or_create_custom_package():
    package, _ = Package.objects.get_or_create(
        name=CUSTOM_PACKAGE_NAME,
        defaults={
            'speed': '-',
            'price': 0,
            'duration_value': SUBSCRIPTION_DAYS,
            'duration_type': 'day',
            'is_active': False,
        },
    )
    return package


def create_renewal_debt(subscriber, amount, due_date, subscription, notes=''):
    """Record subscription renewal amount as debt on the subscriber."""
    from apps.finance.models import Debt

    return Debt.objects.create(
        subscriber=subscriber,
        total_amount=amount,
        due_date=due_date,
        notes=notes or f'دين تجديد اشتراك تلقائي — {subscription.speed}',
        status='pending',
    )


def create_subscriber_subscription(subscriber, package, start_date, auto_renew=True, price=None, user=None, notes=''):
    """Create subscription for a subscriber from a selected package."""
    end_date = package.calculate_end_date(start_date)
    subscription_price = price if price is not None else package.price

    Subscription.objects.filter(subscriber=subscriber, status='active').update(status='expired')

    subscription = Subscription.objects.create(
        subscriber=subscriber,
        package=package,
        speed=package.speed,
        price=subscription_price,
        start_date=start_date,
        end_date=end_date,
        status='active',
        auto_renew=auto_renew,
    )

    SubscriptionHistory.objects.create(
        subscription=subscription,
        action='created',
        notes=notes or f'اشتراك {package.name} — {package.speed}',
        created_by=user,
    )

    subscriber.monthly_price = subscription_price
    subscriber.update_status()
    return subscription


def create_manual_subscription(subscriber, start_date, speed, price, auto_renew=True, user=None, notes=''):
    """Create a 30-day subscription with manually entered speed and price."""
    package = get_or_create_custom_package()
    end_date = start_date + timedelta(days=SUBSCRIPTION_DAYS)

    Subscription.objects.filter(subscriber=subscriber, status='active').update(status='expired')

    subscription = Subscription.objects.create(
        subscriber=subscriber,
        package=package,
        speed=speed,
        price=price,
        start_date=start_date,
        end_date=end_date,
        status='active',
        auto_renew=auto_renew,
    )

    SubscriptionHistory.objects.create(
        subscription=subscription,
        action='created',
        notes=notes or f'اشتراك 30 يوم — {speed}',
        created_by=user,
    )

    subscriber.monthly_price = price
    subscriber.update_status()
    return subscription


def renew_subscription(subscription, package=None, user=None, notes=''):
    """Renew subscription extending from the subscriber's renewal date."""
    package = package or subscription.package
    # Always continue from the subscription's own end date (anniversary),
    # not from "today", so each subscriber keeps their renewal cycle.
    new_start = subscription.end_date
    new_end = package.calculate_end_date(new_start)

    subscription.package = package
    subscription.speed = package.speed
    subscription.price = package.price
    subscription.start_date = new_start
    subscription.end_date = new_end
    subscription.status = 'active'
    subscription.save()

    SubscriptionHistory.objects.create(
        subscription=subscription,
        action='renewed',
        notes=notes or f'تجديد حتى {new_end}',
        created_by=user,
    )

    subscription.subscriber.monthly_price = package.price
    subscription.subscriber.update_status()
    return subscription


def renew_manual_subscription(subscription, user=None, notes='', create_debt=True):
    """Renew subscription for another period based on its package."""
    new_start = subscription.end_date
    package = subscription.package
    if package.name == CUSTOM_PACKAGE_NAME:
        new_end = new_start + timedelta(days=SUBSCRIPTION_DAYS)
    else:
        new_end = package.calculate_end_date(new_start)

    subscription.start_date = new_start
    subscription.end_date = new_end
    subscription.status = 'active'
    subscription.save()

    renewal_notes = notes or f'تجديد تلقائي حتى {new_end}'
    SubscriptionHistory.objects.create(
        subscription=subscription,
        action='renewed',
        notes=renewal_notes,
        created_by=user,
    )

    debt = None
    if create_debt:
        debt = create_renewal_debt(
            subscription.subscriber,
            subscription.price,
            due_date=new_start,
            subscription=subscription,
            notes=f'تجديد اشتراك — {subscription.speed} — {new_start} إلى {new_end}',
        )

    subscription.subscriber.update_status()
    return subscription, debt


def process_auto_renewals(user=None, send_debt_sms=True):
    """Renew overdue subscriptions from each subscriber's own renewal date."""
    from apps.settings_app.models import SystemSettings

    results = {'renewed': 0, 'debts': 0, 'sms_sent': 0, 'sms_failed': 0}

    if not SystemSettings.load().auto_renew_enabled:
        return results

    today = timezone.localdate()
    queryset = Subscription.objects.filter(
        auto_renew=True,
        end_date__lt=today,
        status__in=['active', 'expired'],
    ).select_related('subscriber', 'package')

    for subscription in queryset:
        # Catch up missed periods using the subscriber's renewal anniversary
        # (previous end_date), never shifting the cycle to "today".
        while subscription.end_date < today:
            renewal_from = subscription.end_date
            _, debt = renew_manual_subscription(
                subscription,
                user=user,
                notes='',
            )
            results['renewed'] += 1
            if debt:
                results['debts'] += 1
                if send_debt_sms:
                    from apps.finance.services import send_debt_reminder_sms
                    log, error = send_debt_reminder_sms(debt)
                    if error:
                        results['sms_failed'] += 1
                    elif log and log.status == 'sent':
                        results['sms_sent'] += 1
                    else:
                        results['sms_failed'] += 1
            subscription.refresh_from_db()
            # Safety: avoid infinite loop if dates do not advance
            if subscription.end_date <= renewal_from:
                break

    return results


def expire_overdue_subscriptions():
    """Expire active subscriptions past end_date without auto-renewal."""
    from apps.settings_app.models import SystemSettings

    today = timezone.localdate()
    queryset = Subscription.objects.filter(status='active', end_date__lt=today)

    settings = SystemSettings.load()
    if settings.auto_renew_enabled:
        queryset = queryset.filter(auto_renew=False)

    count = 0
    for subscription in queryset:
        expire_subscription(subscription)
        if settings.auto_suspend_on_expiry:
            subscription.subscriber.is_suspended = True
            subscription.subscriber.status = 'suspended'
            subscription.subscriber.save(update_fields=['is_suspended', 'status', 'updated_at'])
        count += 1
    return count


def create_subscription(subscriber, package, user=None, notes=''):
    """Create new subscription for subscriber."""
    today = timezone.localdate()
    end_date = package.calculate_end_date(today)

    # Expire any existing active subscription
    Subscription.objects.filter(subscriber=subscriber, status='active').update(status='expired')

    subscription = Subscription.objects.create(
        subscriber=subscriber,
        package=package,
        speed=package.speed,
        price=package.price,
        start_date=today,
        end_date=end_date,
        status='active',
    )

    SubscriptionHistory.objects.create(
        subscription=subscription,
        action='created',
        notes=notes,
        created_by=user,
    )

    subscriber.monthly_price = package.price
    subscriber.update_status()
    return subscription


def expire_subscription(subscription, user=None, notes=''):
    subscription.status = 'expired'
    subscription.save()
    SubscriptionHistory.objects.create(
        subscription=subscription,
        action='expired',
        notes=notes,
        created_by=user,
    )
    subscription.subscriber.update_status()


def suspend_subscription(subscription, user=None, notes=''):
    subscription.status = 'suspended'
    subscription.save()
    subscription.subscriber.is_suspended = True
    subscription.subscriber.status = 'suspended'
    subscription.subscriber.save()
    SubscriptionHistory.objects.create(
        subscription=subscription,
        action='suspended',
        notes=notes,
        created_by=user,
    )
