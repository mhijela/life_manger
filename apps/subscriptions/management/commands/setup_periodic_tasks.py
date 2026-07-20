from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from apps.settings_app.models import SystemSettings


class Command(BaseCommand):
    help = 'إعداد مهام Celery Beat للتجديد التلقائي وتنبيهات الاشتراك'

    def handle(self, *args, **options):
        timezone_name = SystemSettings.load().timezone or 'Asia/Gaza'

        daily_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='1',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone=timezone_name,
        )

        alert_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='9',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone=timezone_name,
        )

        cycle_task, created = PeriodicTask.objects.update_or_create(
            name='دورة الاشتراكات اليومية',
            defaults={
                'task': 'apps.dashboard.tasks.run_daily_subscription_cycle',
                'crontab': daily_schedule,
                'enabled': True,
                'description': 'تجديد تلقائي + ترحيل دين + إنهاء الاشتراكات غير المجددة',
            },
        )

        alert_task, alert_created = PeriodicTask.objects.update_or_create(
            name='تنبيهات انتهاء الاشتراك',
            defaults={
                'task': 'apps.dashboard.tasks.send_expiry_alerts',
                'crontab': alert_schedule,
                'enabled': True,
                'description': 'إرسال SMS قبل انتهاء الاشتراك بعدد الأيام المحدد في الإعدادات',
            },
        )

        action = 'تم إنشاء' if created else 'تم تحديث'
        alert_action = 'تم إنشاء' if alert_created else 'تم تحديث'
        self.stdout.write(self.style.SUCCESS(
            f'{action}: {cycle_task.name} — يومياً الساعة 1:00 ({timezone_name})'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'{alert_action}: {alert_task.name} — يومياً الساعة 9:00 ({timezone_name})'
        ))
        self.stdout.write(
            'شغّل Celery worker و beat:\n'
            '  celery -A config worker -l info\n'
            '  celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler'
        )
