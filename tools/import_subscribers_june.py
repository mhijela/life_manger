# -*- coding: utf-8 -*-
"""One-off import of the June 2026 subscriber sheet."""
from datetime import date
from decimal import Decimal

from apps.subscribers.models import Area, Subscriber
from apps.subscriptions.models import Package
from apps.subscriptions.services import create_subscriber_subscription

PACKAGES = {
    '4 ميجا': Decimal('150'),
    '8 ميجا': Decimal('200'),
}

# (username, password, speed, name, address/area, phone, price, day of June)
ROWS = [
    ('447164113855PP', '321531', '4 ميجا', 'شتيوي', 'برج الحرية', '0598838715', 150, 8),
    ('466164242855PP', '843623', '4 ميجا', 'محمد الشوا', 'برج الحرية', '0599537706', 150, 8),
    ('513163864855PP', '341156', '4 ميجا', 'مؤمن السويسي', 'برج الحرية', '0593110917', 120, 15),
    ('568163882855PP', '241265', '4 ميجا', 'عاهد النمرة', 'برج الحرية', '0595156066', 150, 8),
    ('639164264855PP', '187158', '4 ميجا', 'يازجي', 'برج الحرية', '0599980985', 200, 8),
    ('110164196855PP', '328168', '4 ميجا', 'حسن الشاعر', 'برج الحرية', '0599891148', 150, 16),
    ('118164166855PP', '246531', '4 ميجا', 'امير العجلة', 'برج الحرية', '0594078154', 150, 8),
    ('131163967855PP', '138152', '4 ميجا', 'ابو يوسف نجم', 'عمارة الاحلام', '0599601641', 150, 1),
    ('161163948855PP', '684652', '4 ميجا', 'الطيب مختار', 'عمارة الاحلام', '0567609000', 200, 26),
    ('173164281855PP', '343438', '4 ميجا', 'توفيق جبر', 'برج الحرية', '0599055367', 150, 8),
    ('184163743855PP', '113176', '4 ميجا', 'عبد المنعم تعليمي', 'برج مهنا', '0592511530', 100, 1),
    ('265164015855PP', '816272', '4 ميجا', 'راغب', 'العجرمي', '0597188960', 200, 23),
    ('273164054855PP', '445556', '4 ميجا', 'نظام الاشقر', 'عمارة الاحلام', '0598923808', 120, 1),
    ('292164220855PP', '832168', '4 ميجا', 'حمادة حلس', 'برج الحرية', '0594078154', 150, 5),
    ('543264196855PP', '328168', '4 ميجا', 'ابو صائب شقورة', 'العجرمي', '0592179977', 150, 8),
    ('148164166855PP', '246531', '8 ميجا', 'طلال قدوم', 'العجرمي', '0597799401', 150, 8),
    ('183164281855PP', '343438', '4 ميجا', 'برج مهنا جديد', 'برج مهنا', '0566804050', 150, 16),
    ('85527395558PP', '656473', '4 ميجا', 'ابو سالم شمالي', 'برج الحرية', '0594111265', 100, 25),
    ('466194242855PP', '843613', '8 ميجا', 'ابو حسين قدادة', 'عمارة الاحلام', '0597164480', 100, 1),
    ('513193864855PP', '341126', '8 ميجا', 'بسام الاغا', 'عمارة الاحلام', '0599859000', 120, 30),
    ('568193882855PP', '241225', '8 ميجا', 'ابو اسر', 'العجرمي', '0599467060', 200, 8),
    ('85521035558PP', '855210', '8 ميجا', 'سعد الدين', 'عمارة الاحلام', '0595848174', 200, 20),
    ('85522875558PP', '855228', '8 ميجا', 'ترمين', 'عمارة الاحلام', '0598966619', 150, 1),
    ('85527395557PP', '656473', '8 ميجا', 'حميد', 'برج مهنا', '0598184748', 150, 25),
]


def run():
    packages = {}
    for name, default_price in PACKAGES.items():
        pkg, _ = Package.objects.get_or_create(
            name=name,
            defaults={
                'speed': name,
                'price': default_price,
                'duration_value': 30,
                'duration_type': 'day',
                'is_active': True,
            },
        )
        packages[name] = pkg

    areas = {}
    for area_name in {row[4] for row in ROWS}:
        areas[area_name], _ = Area.objects.get_or_create(name=area_name)

    created, skipped = 0, 0
    for username, password, speed, name, area_name, phone, price, day in ROWS:
        if Subscriber.objects.filter(pppoe_username=username).exists():
            skipped += 1
            print(f'skip (already imported): {name} — {username}')
            continue

        price = Decimal(str(price))
        subscriber = Subscriber.objects.create(
            full_name=name,
            phone=phone,
            address=area_name,
            area=areas[area_name],
            pppoe_username=username,
            pppoe_password=password,
            monthly_price=price,
        )
        create_subscriber_subscription(
            subscriber,
            package=packages[speed],
            start_date=date(2026, 6, day),
            auto_renew=True,
            price=price,
        )
        created += 1
        print(f'created: {name} — {speed} — {price} — 2026-06-{day:02d}')

    print(f'\ndone: created={created}, skipped={skipped}')


run()
