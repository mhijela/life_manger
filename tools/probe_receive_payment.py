import json
import re
from pathlib import Path

from apps.finance.jawwal_pay_service import JawwalPayService

svc = JawwalPayService()
svc._load_session()

# CSRF token endpoint
try:
    token_resp = svc._request('GET', '/base/getToken', allow_redirects=True)
    token_data = token_resp.text[:500]
except Exception as exc:
    token_data = str(exc)

text = svc._request('GET', '/merchant/receivePayment', allow_redirects=True).text
Path('tools/jawwal_receive_payment.html').write_text(text, encoding='utf-8')

forms = svc._parse_forms(text)
urls = []
for pat in [r'url\s*:\s*["\']([^"\']+)["\']', r'var\s+url\s*=\s*["\']([^"\']+)["\']', r'\.post\(["\']([^"\']+)["\']']:
    urls.extend(re.findall(pat, text, re.I))

print(json.dumps({
    'page_url': '/merchant/receivePayment',
    'html_len': len(text),
    'forms': forms,
    'urls': list(dict.fromkeys(urls))[:30],
    'inputs': [m.group(1) for m in re.finditer(r'name=["\']([^"\']+)["\']', text, re.I)][:40],
    'functions': re.findall(r'function\s+(\w+)\s*\(', text)[:40],
    'getToken_preview': token_data,
}, ensure_ascii=False, indent=2))
