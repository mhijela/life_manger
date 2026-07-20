import json
import re
from pathlib import Path

from apps.finance.jawwal_pay_service import JawwalPayService

svc = JawwalPayService()
svc._load_session()
text = svc._request('GET', '/merchant/requestPaymentServices', allow_redirects=True).text
Path('tools/jawwal_payment_page.html').write_text(text, encoding='utf-8')

checks = {
    'iframes': re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', text, re.I),
    'includes': re.findall(r'(?:ng-include|data-url|href)=["\']([^"\']+)["\']', text, re.I)[:30],
    'inputs': [m.group(1) for m in re.finditer(r'name=["\']([^"\']+)["\']', text, re.I)][:40],
    'functions': re.findall(r'function\s+(\w*(?:payment|Payment|request|Request|sms|SMS)\w*)\s*\(', text)[:30],
    'data_actions': re.findall(r'data-[a-z-]+=["\']([^"\']+)["\']', text, re.I)[:30],
}
print(json.dumps(checks, ensure_ascii=False, indent=2))
