import json
import re

from apps.finance.jawwal_pay_service import JawwalPayService

svc = JawwalPayService()
svc._load_session()
text = svc._request('GET', '/merchant/requestPaymentServices', allow_redirects=True).text

patterns = [
    r'url\s*:\s*["\']([^"\']+)["\']',
    r'var\s+url\s*=\s*["\']([^"\']+)["\']',
    r'\.post\(["\']([^"\']+)["\']',
    r'fetch\(["\']([^"\']+)["\']',
    r'action\s*=\s*["\']([^"\']+)["\']',
]
found = []
for pat in patterns:
    found.extend(re.findall(pat, text, re.I))

keywords = ('payment', 'request', 'sms', 'send', 'merchant', 'wallet', 'save', 'submit')
filtered = [u for u in dict.fromkeys(found) if any(k in u.lower() for k in keywords) or u.startswith('/merchant/')]

contexts = []
for m in re.finditer(r'.{0,120}(requestPayment|sendPayment|paymentServices|receivePayment).{0,200}', text, re.I | re.S):
    contexts.append(re.sub(r'\s+', ' ', m.group(0))[:400])

print(json.dumps({'filtered_urls': filtered[:40], 'contexts': contexts[:15]}, ensure_ascii=False, indent=2))
