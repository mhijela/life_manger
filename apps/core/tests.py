"""
Smoke + deploy-critical tests for INMS.
Run: python manage.py test
"""
from decimal import Decimal
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse, NoReverseMatch

from apps.finance.models import Debt, DebtPayment, Payment, PaymentMethod
from apps.subscribers.models import Subscriber
from apps.subscriptions.models import Package
from apps.subscriptions.services import create_subscriber_subscription

User = get_user_model()


class HealthCheckTests(TestCase):
    def test_healthz_ok_without_login(self):
        r = self.client.get('/healthz/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), 'ok')

    def test_healthz_ok_when_no_superuser(self):
        User.objects.all().delete()
        r = self.client.get('/healthz/')
        self.assertEqual(r.status_code, 200)


class InitialSetupTests(TestCase):
    def test_redirects_to_setup_when_no_admin(self):
        User.objects.all().delete()
        r = self.client.get('/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/setup/', r.url)

    def test_setup_creates_superuser_and_logs_in(self):
        User.objects.all().delete()
        r = self.client.post('/accounts/setup/', {
            'first_name': 'Admin',
            'email': 'admin@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(r.status_code, 302)
        user = User.objects.get(email='admin@example.com')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_setup_blocked_when_admin_exists(self):
        User.objects.create_superuser(
            email='exists@example.com', password='StrongPass123!', first_name='A'
        )
        r = self.client.get('/accounts/setup/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r.url)


class UrlSmokeTests(TestCase):
    """Ensure critical named routes reverse without errors."""

    REQUIRED_NAMES = [
        'healthz',
        'dashboard:index',
        'accounts:login',
        'accounts:setup',
        'subscribers:list',
        'subscribers:create',
        'subscriptions:packages',
        'finance:index',
        'finance:debts',
        'daily_tasks:list',
        'settings_app:index',
        'reports:index',
    ]

    def test_required_urls_reverse(self):
        for name in self.REQUIRED_NAMES:
            try:
                reverse(name)
            except NoReverseMatch as exc:
                self.fail(f'URL name failed to reverse: {name} ({exc})')


class AuthPagesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email='admin@test.local', password='StrongPass123!', first_name='Admin'
        )

    def test_login_page_loads(self):
        r = self.client.get(reverse('accounts:login'))
        self.assertEqual(r.status_code, 200)

    def test_dashboard_requires_login(self):
        r = self.client.get(reverse('dashboard:index'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r.url)

    def test_dashboard_ok_when_logged_in(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse('dashboard:index'))
        self.assertEqual(r.status_code, 200)

    def test_subscribers_list_ok(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse('subscribers:list'))
        self.assertEqual(r.status_code, 200)


class SubscriberHubTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email='admin@test.local', password='StrongPass123!', first_name='Admin'
        )
        self.client.force_login(self.user)
        self.method = PaymentMethod.objects.create(name='نقدي', is_active=True)
        self.package = Package.objects.create(
            name='4 ميجا', speed='4Mbps', price=Decimal('100.00'),
            duration_value=30, duration_type='day', is_active=True,
        )
        self.subscriber = Subscriber.objects.create(
            full_name='مشترك تجريبي', phone='0599000000', monthly_price=Decimal('100.00'),
        )
        self.subscription = create_subscriber_subscription(
            self.subscriber, package=self.package,
            start_date=date.today(), auto_renew=True, user=self.user,
        )

    def test_detail_page_loads(self):
        r = self.client.get(reverse('subscribers:detail', args=[self.subscriber.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'تسجيل قبض')

    def test_hub_pay_creates_payment(self):
        r = self.client.post(reverse('subscribers:hub_pay', args=[self.subscriber.pk]), {
            'amount': '50.00',
            'payment_date': date.today().isoformat(),
            'method': self.method.pk,
            'description': 'test',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            Payment.objects.filter(subscriber=self.subscriber, amount=Decimal('50.00')).exists()
        )

    def test_hub_renew(self):
        old_end = self.subscription.end_date
        r = self.client.post(reverse('subscribers:hub_renew', args=[self.subscriber.pk]), {
            'package': self.package.pk,
            'create_debt': 'on',
        })
        self.assertEqual(r.status_code, 302)
        self.subscription.refresh_from_db()
        self.assertGreater(self.subscription.end_date, old_end)
        self.assertTrue(Debt.objects.filter(subscriber=self.subscriber).exists())


class DebtPaymentPersistenceTests(TestCase):
    """Regression: paid_amount must be saved with status."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            email='admin@test.local', password='StrongPass123!', first_name='Admin'
        )
        self.method = PaymentMethod.objects.create(name='بنك', is_active=True)
        self.subscriber = Subscriber.objects.create(
            full_name='مدين', phone='0599111111', monthly_price=Decimal('150.00'),
        )
        self.debt = Debt.objects.create(
            subscriber=self.subscriber,
            total_amount=Decimal('150.00'),
            due_date=date.today(),
            status='pending',
        )

    def test_update_status_persists_paid_amount(self):
        self.debt.paid_amount = Decimal('150.00')
        self.debt.update_status()
        self.debt.refresh_from_db()
        self.assertEqual(self.debt.paid_amount, Decimal('150.00'))
        self.assertEqual(self.debt.status, 'paid')

    def test_hub_settle_marks_paid_and_creates_payment(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse('subscribers:hub_settle_debt', args=[self.subscriber.pk]),
            {
                'debt_id': self.debt.pk,
                'amount': '150.00',
                'payment_date': date.today().isoformat(),
                'method': self.method.pk,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.debt.refresh_from_db()
        self.assertEqual(self.debt.status, 'paid')
        self.assertEqual(self.debt.paid_amount, Decimal('150.00'))
        self.assertTrue(Payment.objects.filter(subscriber=self.subscriber).exists())
        self.assertTrue(DebtPayment.objects.filter(debt=self.debt).exists())


class SettingsSmokeTests(TestCase):
    def test_celery_eager_without_redis(self):
        from django.conf import settings
        self.assertTrue(settings.CELERY_TASK_ALWAYS_EAGER)
