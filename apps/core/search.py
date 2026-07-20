from django.db.models import Q
from django.urls import reverse


def _item(category, icon, title, subtitle, url):
    return {
        'category': category,
        'icon': icon,
        'title': title,
        'subtitle': subtitle,
        'url': url,
    }


def global_search(query, limit_per_group=5):
    query = (query or '').strip()
    if len(query) < 2:
        return {'query': query, 'groups': [], 'total': 0}

    groups = []
    total = 0

    from apps.subscribers.models import Subscriber

    subscribers = Subscriber.objects.filter(
        Q(full_name__icontains=query)
        | Q(phone__icontains=query)
        | Q(whatsapp__icontains=query)
        | Q(ip_address__icontains=query)
        | Q(mac_address__icontains=query)
        | Q(pppoe_username__icontains=query)
        | Q(address__icontains=query)
    ).select_related('area')[:limit_per_group]

    if subscribers:
        items = [
            _item(
                'subscribers',
                'bi-people-fill',
                s.full_name,
                f'{s.phone} · {s.get_status_display()}',
                reverse('subscribers:detail', args=[s.pk]),
            )
            for s in subscribers
        ]
        groups.append({'key': 'subscribers', 'label': 'المشتركون', 'items': items})
        total += len(items)

    from apps.devices.models import Device

    devices = Device.objects.filter(
        Q(name__icontains=query)
        | Q(ip_address__icontains=query)
        | Q(mac_address__icontains=query)
        | Q(location__icontains=query)
        | Q(serial_number__icontains=query)
    ).select_related('subscriber')[:limit_per_group]

    if devices:
        items = [
            _item(
                'devices',
                'bi-router-fill',
                d.name,
                d.ip_address or d.get_device_type_display(),
                reverse('devices:detail', args=[d.pk]),
            )
            for d in devices
        ]
        groups.append({'key': 'devices', 'label': 'الأجهزة', 'items': items})
        total += len(items)

    from apps.subscriptions.models import Subscription

    subscriptions = Subscription.objects.filter(
        Q(subscriber__full_name__icontains=query)
        | Q(subscriber__phone__icontains=query)
        | Q(package__name__icontains=query)
    ).select_related('subscriber', 'package')[:limit_per_group]

    if subscriptions:
        items = [
            _item(
                'subscriptions',
                'bi-calendar-check-fill',
                sub.subscriber.full_name,
                f'{sub.package.name} · {sub.get_status_display()}',
                reverse('subscribers:detail', args=[sub.subscriber_id]),
            )
            for sub in subscriptions
        ]
        groups.append({'key': 'subscriptions', 'label': 'الاشتراكات', 'items': items})
        total += len(items)

    from apps.finance.models import Debt

    debts = Debt.objects.filter(
        Q(subscriber__full_name__icontains=query)
        | Q(subscriber__phone__icontains=query)
        | Q(notes__icontains=query)
    ).exclude(status='paid').select_related('subscriber')[:limit_per_group]

    if debts:
        items = [
            _item(
                'debts',
                'bi-wallet2',
                d.subscriber.full_name,
                f'متبقي {d.remaining_amount} · {d.get_status_display()}',
                reverse('subscribers:detail', args=[d.subscriber_id]),
            )
            for d in debts
        ]
        groups.append({'key': 'debts', 'label': 'الديون', 'items': items})
        total += len(items)

    from apps.inventory.models import InventoryItem

    inventory = InventoryItem.objects.filter(
        Q(name__icontains=query) | Q(category__icontains=query) | Q(supplier__icontains=query)
    )[:limit_per_group]

    if inventory:
        items = [
            _item(
                'inventory',
                'bi-box-seam-fill',
                item.name,
                f'الكمية: {item.quantity}',
                reverse('inventory:list') + f'?q={query}',
            )
            for item in inventory
        ]
        groups.append({'key': 'inventory', 'label': 'المخزون', 'items': items})
        total += len(items)

    from apps.assets.models import Asset

    assets = Asset.objects.filter(
        Q(name__icontains=query)
        | Q(serial_number__icontains=query)
        | Q(assigned_to__full_name__icontains=query)
    ).select_related('assigned_to', 'category')[:limit_per_group]

    if assets:
        items = [
            _item(
                'assets',
                'bi-hdd-stack-fill',
                a.name,
                a.assigned_to.full_name if a.assigned_to else a.get_status_display(),
                reverse('assets:detail', args=[a.pk]),
            )
            for a in assets
        ]
        groups.append({'key': 'assets', 'label': 'الأصول', 'items': items})
        total += len(items)

    return {'query': query, 'groups': groups, 'total': total}
