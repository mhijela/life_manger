import json
import os
import re

from apps.finance.jawwal_pay_service import JawwalPayService

MOBILE = os.environ.get('JAWWAL_MOBILE', '0595108208')
AMOUNT = os.environ.get('JAWWAL_AMOUNT', '5')

svc = JawwalPayService()
svc._load_session()

page = svc._request('GET', '/merchant/receivePayment', allow_redirects=True)
forms = svc._parse_forms(page.text)
form = forms[0]
hidden = {i['name']: i['value'] for i in form.get('inputs', []) if i.get('type') == 'hidden'}
phone = '0595108208' if MOBILE.startswith('0') else '0' + svc._normalize_phone(MOBILE)
payload = {**hidden, 'amount': str(AMOUNT), 'customerMobileNumber': phone, 'confirmMobileNumber': phone}
action = form.get('action') or '/merchant/confirmReceivePayment/receivePaymentForm'
resp = svc._request('POST', action, data=payload, allow_redirects=True)
text = resp.text

confirm_forms = svc._parse_forms(text)
urls = re.findall(r'var\s+url\s*=\s*["\']([^"\']+)["\']', text)
success_msgs = re.findall(r'alert-success[^>]*>(.*?)</div>', text, re.S | re.I)
danger_msgs = re.findall(r'alert-danger[^>]*>(.*?)</div>', text, re.S | re.I)

print(json.dumps({
    'step1_success': 'Request Rejected' not in text,
    'final_url': resp.url,
    'confirm_forms': confirm_forms,
    'script_urls': urls[:10],
    'success_msgs': [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m)).strip() for m in success_msgs[:3]],
    'danger_msgs': [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m)).strip() for m in danger_msgs[:3]],
    'title': re.search(r'<title>\s*([^<]+)', text, re.I).group(1).strip() if re.search(r'<title>', text, re.I) else '',
}, ensure_ascii=False, indent=2))
