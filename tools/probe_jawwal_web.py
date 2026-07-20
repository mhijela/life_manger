"""Probe Jawwal Pay business portal pages."""
import re
import requests

s = requests.Session()
s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
base = 'https://business.jawwalpay.ps'

for path in ['/login/auth', '/merchant/requestPaymentServices']:
    r = s.get(base + path, allow_redirects=True, timeout=30)
    print('===', path, '->', r.url, r.status_code)
    forms = re.findall(r'<form[^>]*>(.*?)</form>', r.text, re.S | re.I)
    print('forms:', len(forms))
    for i, f in enumerate(forms[:5]):
        action_m = re.search(r'action=["\']([^"\']*)', f, re.I)
        inputs = re.findall(r'name=["\']([^"\']+)["\']', f, re.I)
        print(' form', i, 'action', action_m.group(1) if action_m else None, 'inputs', inputs)
    urls = re.findall(r'(?:fetch|axios|\.post|url:\s*)["\']([^"\']+)["\']', r.text)
    print('urls:', list(dict.fromkeys(urls))[:25])
    print('cookies:', list(s.cookies.keys()))
    print('len html', len(r.text))
    print()
