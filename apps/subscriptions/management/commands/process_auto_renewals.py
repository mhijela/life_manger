from django.core.management.base import BaseCommand

from apps.subscriptions.services import process_auto_renewals


class Command(BaseCommand):
    help = 'تجديد الاشتراكات المنتهية التي لديها تجديد تلقائي مفعّل وترحيل الدين'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-sms',
            action='store_true',
            help='عدم إرسال SMS تذكير الدين بعد التجديد',
        )

    def handle(self, *args, **options):
        results = process_auto_renewals(send_debt_sms=not options['no_sms'])
        renewed = results['renewed']
        if renewed:
            msg = (
                f'تم تجديد {renewed} اشتراك، '
                f'ترحيل {results["debts"]} دين، '
                f'SMS: {results["sms_sent"]} ناجح / {results["sms_failed"]} فاشل'
            )
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stdout.write('لا توجد اشتراكات تحتاج تجديداً.')
