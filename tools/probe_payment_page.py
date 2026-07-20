import json
import re

from apps.finance.jawwal_pay_service import JawwalPayService

svc = JawwalPayService()
svc._load_session()
text = svc._request('GET', '/merchant/requestPaymentServices', allow_redirects=True).text
urls = sorted(set(re.findall(r'["\'](/[^"\']+)["\']', text)))
hits = [u for u in urls if any(k in u.lower() for k in ('payment', 'request', 'sms', 'merchant', 'send', 'wallet', 'transfer'))]
scripts = re.findall(r'src=["\']([^"\']+)["\']', text)
print(json.dumps({
    'html_len': len(text),
    'hits': hits[:50],
    'scripts': scripts[:30],
    'title_snip': re.search(r'<title>([^<]+)</title>', text, re.I).group(1) if re.search(r'<title>', text, re.I) else '',
}, ensure_ascii=False, indent=2))
