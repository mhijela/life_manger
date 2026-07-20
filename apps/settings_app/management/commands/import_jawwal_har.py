from pathlib import Path

from django.core.management.base import BaseCommand

from apps.finance.jawwal_har import discover_from_har
from apps.finance.jawwal_pay_service import JawwalPayService


class Command(BaseCommand):
    help = 'Import Jawwal Pay API endpoints from a browser HAR export'

    def add_arguments(self, parser):
        parser.add_argument('har_file', help='Path to exported .har file')
        parser.add_argument('--apply', action='store_true', help='Save discovered URLs into SystemSettings')

    def handle(self, *args, **options):
        discovery = discover_from_har(Path(options['har_file']))
        self.stdout.write(f"POST endpoints: {len(discovery['endpoints'])}")
        for item in discovery['endpoints']:
            self.stdout.write(
                f"- {item['method']} {item['path']} action={item['action']} status={item['status']}"
            )

        if options['apply']:
            JawwalPayService.apply_har_discovery(discovery)
            self.stdout.write(self.style.SUCCESS('Applied to SystemSettings.'))
        else:
            self.stdout.write('Run again with --apply to persist URLs/field map.')
