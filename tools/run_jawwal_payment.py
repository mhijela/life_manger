"""Validate OTP and run SMS payment request in one session."""
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from apps.finance.jawwal_pay_service import JawwalPayService

OTP = sys.argv[1] if len(sys.argv) > 1 else ''
MOBILE = sys.argv[2] if len(sys.argv) > 2 else '0595108208'
AMOUNT = sys.argv[3] if len(sys.argv) > 3 else '5'

svc = JawwalPayService()
otp_result = svc.validate_otp(OTP)

out = {
    'otp_success': otp_result.get('success'),
    'otp_error': otp_result.get('error'),
    'otp_message': otp_result.get('message'),
    'authenticated': svc.is_authenticated(),
}

if otp_result.get('success'):
    pay_page = svc._request('GET', '/merchant/requestPaymentServices', allow_redirects=True)
    out['payment_page_url'] = pay_page.url
    out['payment_authed'] = svc._is_authenticated_html(pay_page.text, pay_page.url)
    out['ajax_urls'] = svc._extract_ajax_urls(pay_page.text)[:25]
    out['forms'] = svc._parse_forms(pay_page.text)[:3]
    out['payment_spec'] = svc.discover_payment_request(pay_page.text, pay_page.url)

    payment = svc.request_payment_sms(MOBILE, AMOUNT, '')
    resp = payment.get('response')
    out['payment_result'] = {
        'success': payment.get('success'),
        'error': payment.get('error'),
        'status_code': payment.get('status_code'),
        'request': payment.get('request'),
        'response': resp if isinstance(resp, dict) else str(resp)[:2000],
    }
else:
    out['otp_response'] = otp_result.get('response')

print(json.dumps(out, ensure_ascii=False, indent=2))
