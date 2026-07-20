"""Parse Jawwal Pay HAR exports from browser DevTools."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_HOST = 'business.jawwalpay.ps'


def _parse_post_data(raw: str | None, mime: str | None) -> dict:
    if not raw:
        return {}
    mime = (mime or '').lower()
    if 'json' in mime:
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {'_json': data}
        except json.JSONDecodeError:
            return {'_raw': raw}
    if 'form' in mime or '=' in raw:
        parsed = parse_qs(raw, keep_blank_values=True)
        return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
    return {'_raw': raw}


def _classify(path: str, payload: dict) -> str | None:
    blob = f'{path} {json.dumps(payload, ensure_ascii=False)}'.lower()
    if any(k in blob for k in ('transfer', 'تحويل', 'moneytransfer')):
        return 'transfer'
    if any(k in blob for k in ('requestpayment', 'request', 'sms', 'مطالبة', 'دفعة')):
        return 'request_payment'
    return None


def _payload_to_template(payload: dict) -> dict:
    templates = {}
    for key, value in payload.items():
        if key.startswith('_'):
            continue
        text = str(value)
        if text.isdigit() and len(text) >= 9:
            templates[key] = '{mobile}'
        elif text.replace('.', '', 1).isdigit():
            templates[key] = '{amount}'
        elif text:
            templates[key] = '{note}'
        else:
            templates[key] = ''
    return templates


def discover_from_har(har_path: Path | str) -> dict:
    har_path = Path(har_path)
    har = json.loads(har_path.read_text(encoding='utf-8'))
    entries = har.get('log', {}).get('entries', [])

    result = {
        'source': str(har_path),
        'endpoints': [],
        'login_post': '',
        'login_payload': {},
        'request_payment_url': '',
        'transfer_url': '',
        'field_map': {'request_payment': {}, 'transfer': {}},
    }

    for entry in entries:
        req = entry.get('request', {})
        url = req.get('url', '')
        if BASE_HOST not in url:
            continue
        if req.get('method') not in ('POST', 'PUT', 'PATCH'):
            continue

        parsed = urlparse(url)
        post_data = req.get('postData', {})
        payload = _parse_post_data(post_data.get('text'), post_data.get('mimeType'))

        if '/login/authenticate' in parsed.path or 'username' in payload and 'password' in payload:
            result['login_post'] = parsed.path
            result['login_payload'] = payload
            result['endpoints'].append({
                'method': req.get('method'),
                'path': parsed.path,
                'url': url,
                'payload': payload,
                'action': 'login',
                'status': entry.get('response', {}).get('status'),
            })
            continue

        if '/login/twofactorauth' in parsed.path.lower() or (
            'otp' in payload or 'token' in payload and 'password' not in payload
        ):
            result.setdefault('otp_post', parsed.path)
            result.setdefault('otp_payload', payload)
            result['endpoints'].append({
                'method': req.get('method'),
                'path': parsed.path,
                'url': url,
                'payload': payload,
                'action': 'otp',
                'status': entry.get('response', {}).get('status'),
            })
            continue

        if any(x in parsed.path for x in ('/TSPD/', '/assets/')):
            continue

        post_data = req.get('postData', {})
        payload = _parse_post_data(post_data.get('text'), post_data.get('mimeType'))
        action = _classify(parsed.path, payload)

        item = {
            'method': req.get('method'),
            'path': parsed.path,
            'url': url,
            'payload': payload,
            'action': action,
            'status': entry.get('response', {}).get('status'),
        }
        result['endpoints'].append(item)

        if action == 'request_payment' and not result['request_payment_url']:
            result['request_payment_url'] = parsed.path
            result['field_map']['request_payment'] = _payload_to_template(payload)
        if action == 'transfer' and not result['transfer_url']:
            result['transfer_url'] = parsed.path
            result['field_map']['transfer'] = _payload_to_template(payload)

    return result
