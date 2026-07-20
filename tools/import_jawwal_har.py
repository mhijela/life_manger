"""Extract Jawwal Pay merchant API calls from a Chrome/Edge HAR export."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from apps.finance.jawwal_har import discover_from_har


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python tools/import_jawwal_har.py path/to/export.har [--apply]')
        return 1

    har_path = Path(sys.argv[1])
    if not har_path.exists():
        print(f'File not found: {har_path}')
        return 1

    discovery = discover_from_har(har_path)
    out_path = har_path.with_suffix('.discovery.json')
    out_path.write_text(json.dumps(discovery, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Found {len(discovery["endpoints"])} POST endpoints')
    for item in discovery['endpoints']:
        print(f"- {item['method']} {item['path']}  action={item['action']}  status={item['status']}")

    if discovery['request_payment_url']:
        print(f"\nrequest_payment_url: {discovery['request_payment_url']}")
    if discovery['transfer_url']:
        print(f"transfer_url: {discovery['transfer_url']}")

    print(f'\nSaved: {out_path}')

    if '--apply' in sys.argv[2:]:
        from apps.finance.jawwal_pay_service import JawwalPayService

        JawwalPayService.apply_har_discovery(discovery)
        print('Applied discovery to SystemSettings.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
