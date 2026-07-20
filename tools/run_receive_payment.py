import json
import os
import re

from apps.finance.jawwal_pay_service import JawwalPayService

MOBILE = os.environ.get('JAWWAL_MOBILE', '0595108208')
AMOUNT = os.environ.get('JAWWAL_AMOUNT', '5')

svc = JawwalPayService()
svc._load_session()

if not svc.is_authenticated():
    print(json.dumps({'success': False, 'error': 'غير مسجل دخول — أعد OTP'}, ensure_ascii=False))
    raise SystemExit(1)

page = svc._request('GET', '/merchant/receivePayment', allow_redirects=True)
forms = svc._parse_forms(page.text)
form = forms[0] if forms else {}
hidden = {i['name']: i['value'] for i in form.get('inputs', []) if i.get('type') == 'hidden'}
phone = svc._normalize_phone(MOBILE)
if phone.startswith('5'):
    phone = '0' + phone

payload = {
    **hidden,
    'amount': str(AMOUNT),
    'customerMobileNumber': phone,
    'confirmMobileNumber': phone,
}
action = form.get('action') or '/merchant/confirmReceivePayment/receivePaymentForm'

response = svc._request('POST', action, data=payload, allow_redirects=True)
content_type = response.headers.get('content-type', '').lower()
body = response.text or ''
result = {
    'success': response.ok and 'alert-danger' not in body and 'Request Rejected' not in body,
    'request': {
        'method': 'POST',
        'path': action,
        'payload': payload,
    },
    'response': {
        'status_code': response.status_code,
        'final_url': response.url,
        'content_type': content_type,
        'preview': body[:3000],
    },
}
if 'alert-success' in body or 'تم' in body:
    result['success'] = True
if 'alert-danger' in body or 'خطأ' in body:
    result['success'] = False
    m = re.search(r'alert-danger[^>]*>.*?([^<]+)', body, re.S | re.I)
    if m:
        result['error'] = re.sub(r'\s+', ' ', m.group(1)).strip()

svc._save_session({'authenticated': True, 'otp_pending': False})
print(json.dumps(result, ensure_ascii=False, indent=2))
