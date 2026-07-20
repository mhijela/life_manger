from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class Command(BaseCommand):
    help = 'تحميل بيانات تجريبية للنظام'

    def handle(self, *args, **options):
        from apps.accounts.models import User, UserProfile
        from apps.settings_app.models import SystemSettings
        from apps.subscribers.models import Area, Subscriber
        from apps.subscriptions.models import Package, Subscription, SubscriptionHistory
        from apps.finance.models import PaymentMethod, Payment, ExpenseCategory, Expense, Debt
        from apps.inventory.models import Unit, InventoryItem
        from apps.assets.models import AssetCategory, Asset
        from apps.devices.models import Device
        from apps.messages.models import MessageTemplate

        self.stdout.write('جاري تحميل البيانات التجريبية...')

        # Admin user
        if not User.objects.filter(email='admin@inms.local').exists():
            user = User.objects.create_superuser(
                email='admin@inms.local',
                password='admin123',
                first_name='مدير',
                last_name='النظام',
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.phone = '0599000000'
            profile.save()
            self.stdout.write(self.style.SUCCESS('تم إنشاء المستخدم: admin@inms.local / admin123'))

        # Settings
        settings = SystemSettings.load()
        settings.company_name = 'شبكة النور للإنترنت'
        settings.currency = 'ILS'
        settings.currency_symbol = '₪'
        settings.save()

        # Areas
        areas = {}
        for name in ['الوسطى', 'الشمال', 'الجنوب', 'الشرق']:
            areas[name], _ = Area.objects.get_or_create(name=name)

        # Payment methods
        for name in ['نقدي', 'تحويل بنكي', 'محفظة إلكترونية']:
            PaymentMethod.objects.get_or_create(name=name)

        # Expense categories
        for name in ['صيانة', 'رواتب', 'إيجار', 'معدات', 'أخرى']:
            ExpenseCategory.objects.get_or_create(name=name, defaults={'is_default': True})

        # Units
        for name in ['قطعة', 'متر', 'كرتونة']:
            Unit.objects.get_or_create(name=name)

        # Packages
        packages = []
        pkg_data = [
            ('أساسي', '5 ميجا', Decimal('80'), 1, 'month'),
            ('متوسط', '10 ميجا', Decimal('120'), 1, 'month'),
            ('مميز', '20 ميجا', Decimal('180'), 1, 'month'),
        ]
        for name, speed, price, dur, dur_type in pkg_data:
            pkg, _ = Package.objects.get_or_create(
                name=name, defaults={'speed': speed, 'price': price, 'duration_value': dur, 'duration_type': dur_type}
            )
            packages.append(pkg)

        # Asset categories
        router_cat, _ = AssetCategory.objects.get_or_create(name='راوتر')
        AssetCategory.objects.get_or_create(name='كابل')

        # Subscribers
        today = timezone.now().date()
        subscribers_data = [
            ('أحمد محمد علي', '0599111111', 'الوسطى', packages[1], 'active'),
            ('محمود حسن', '0599222222', 'الشمال', packages[0], 'active'),
            ('سارة أحمد', '0599333333', 'الجنوب', packages[2], 'expired'),
            ('خالد يوسف', '0599444444', 'الشرق', packages[1], 'debtor'),
            ('فاطمة إبراهيم', '0599555555', 'الوسطى', packages[0], 'active'),
        ]

        cash_method = PaymentMethod.objects.first()

        for full_name, phone, area_name, pkg, status in subscribers_data:
            sub, created = Subscriber.objects.get_or_create(
                phone=phone,
                defaults={
                    'full_name': full_name,
                    'whatsapp': phone,
                    'area': areas[area_name],
                    'address': f'شارع الرئيسي - {area_name}',
                    'monthly_price': pkg.price,
                    'status': status,
                    'router_name': f'Router-{phone[-4:]}',
                    'ip_address': f'192.168.1.{phone[-2:]}',
                },
            )
            if created:
                end = today + timedelta(days=30) if status == 'active' else today - timedelta(days=5)
                start = end - timedelta(days=30)
                subscription = Subscription.objects.create(
                    subscriber=sub, package=pkg, speed=pkg.speed, price=pkg.price,
                    start_date=start, end_date=end,
                    status='active' if status == 'active' else 'expired',
                )
                SubscriptionHistory.objects.create(subscription=subscription, action='created')
                Payment.objects.create(
                    subscriber=sub, amount=pkg.price, method=cash_method,
                    description=f'دفعة اشتراك {pkg.name}',
                )
                if status == 'debtor':
                    Debt.objects.create(
                        subscriber=sub, total_amount=Decimal('120'),
                        paid_amount=Decimal('50'), due_date=today + timedelta(days=15),
                        status='partial',
                    )

        # Inventory
        unit = Unit.objects.first()
        for name, qty, min_s in [('راوتر TP-Link', 15, 5), ('كابل شبكة', 100, 20), ('موصل RJ45', 200, 50)]:
            InventoryItem.objects.get_or_create(
                name=name, defaults={'quantity': qty, 'unit': unit, 'min_stock': min_s, 'category': 'معدات'}
            )

        # Devices
        Device.objects.get_or_create(
            name='راوتر رئيسي', defaults={
                'device_type': 'router', 'ip_address': '10.0.0.1',
                'location': 'غرفة السيرفر', 'status': 'active',
            }
        )
        Device.objects.get_or_create(
            name='سويتش الطابق الأول', defaults={
                'device_type': 'switch', 'ip_address': '10.0.0.2',
                'location': 'الطابق الأول', 'status': 'active',
            }
        )

        # Assets
        sub = Subscriber.objects.first()
        if sub:
            Asset.objects.get_or_create(
                name='راوتر أحمد', defaults={
                    'serial_number': 'RT-001', 'category': router_cat,
                    'assigned_to': sub, 'assignment_date': today, 'status': 'assigned',
                }
            )

        # Expenses
        cat = ExpenseCategory.objects.first()
        Expense.objects.get_or_create(
            title='صيانة أبراج', defaults={'amount': Decimal('500'), 'category': cat}
        )

        # Message templates
        templates = [
            ('تذكير انتهاء اشتراك', 'expiry_reminder', 'عزيزي {name}، اشتراكك ينتهي في {expiry_date}. يرجى التجديد.'),
            ('تذكير دين', 'debt_reminder', 'عزيزي {name}، لديك مبلغ {amount} مستحق. يرجى السداد.'),
            ('تأكيد دفع', 'payment_confirmation', 'عزيزي {name}، تم استلام دفعتك بمبلغ {amount}. شكراً لك.'),
            ('تنبيه صيانة', 'maintenance_alert', 'عزيزي {name}، سيتم إجراء صيانة على الشبكة. نعتذر عن الإزعاج.'),
            ('إعلان عام', 'general', 'إعلان من {company}: {name}'),
        ]
        for name, ttype, body in templates:
            MessageTemplate.objects.get_or_create(name=name, defaults={'template_type': ttype, 'body': body})

        debt_tpl = MessageTemplate.objects.filter(template_type='debt_reminder', is_active=True).first()
        sys_settings = SystemSettings.load()
        if debt_tpl and not sys_settings.debt_sms_template_id:
            sys_settings.debt_sms_template = debt_tpl
            sys_settings.save(update_fields=['debt_sms_template'])

        self.stdout.write(self.style.SUCCESS('تم تحميل البيانات التجريبية بنجاح!'))
