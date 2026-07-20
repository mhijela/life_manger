"""
Capture Jawwal Pay Business Portal network requests via Playwright.
Usage:
  python tools/capture_jawwal_network.py

Steps:
  1. Browser opens on the merchant portal
  2. Log in manually if needed
  3. Perform transfer + SMS payment request
  4. Press Enter in the terminal when done
  5. Requests saved to tools/jawwal_captured_requests.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import argparse
import time

from playwright.sync_api import sync_playwright

BASE_URL = 'https://business.jawwalpay.ps'
START_URL = f'{BASE_URL}/merchant/requestPaymentServices'
OUTPUT = Path(__file__).resolve().parent / 'jawwal_captured_requests.json'
STORAGE = Path(__file__).resolve().parent / 'jawwal_session.json'

INTERESTING_KEYWORDS = (
    'merchant', 'payment', 'transfer', 'request', 'sms', 'api', 'service', 'wallet', 'otp', 'pin'
)


def _is_interesting(url: str) -> bool:
    lower = url.lower()
    if not lower.startswith(BASE_URL):
        return False
    if any(x in lower for x in ('.css', '.js', '.png', '.svg', '.woff', '.ico', '/TSPD/', '/assets/')):
        return False
    return any(k in lower for k in INTERESTING_KEYWORDS) or '/merchant/' in lower


def _safe_body(body: bytes | str | None, limit: int = 8000) -> str | None:
    if body is None:
        return None
    if isinstance(body, bytes):
        try:
            text = body.decode('utf-8')
        except UnicodeDecodeError:
            return f'<binary {len(body)} bytes>'
    else:
        text = body
    if len(text) > limit:
        return text[:limit] + '...<truncated>'
    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Capture Jawwal Pay Business Portal network traffic')
    parser.add_argument(
        '--auto-timeout',
        type=int,
        default=0,
        help='Seconds to keep capturing before auto-save (0 = wait for ENTER)',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    captured: list[dict] = []

    def on_request(request):
        url = request.url
        if not _is_interesting(url):
            return
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'method': request.method,
            'url': url,
            'path': urlparse(url).path,
            'query': urlparse(url).query,
            'resource_type': request.resource_type,
            'headers': dict(request.headers),
            'post_data': _safe_body(request.post_data),
        }
        captured.append(entry)
        print(f'[REQ] {request.method} {urlparse(url).path}')

    def on_response(response):
        url = response.url
        if not _is_interesting(url):
            return
        req = response.request
        body = None
        try:
            if response.headers.get('content-type', '').startswith(('application/json', 'text/')):
                body = _safe_body(response.text())
        except Exception as exc:
            body = f'<could not read body: {exc}>'
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'response',
            'method': req.method,
            'url': url,
            'path': urlparse(url).path,
            'status': response.status,
            'headers': dict(response.headers),
            'body': body,
        }
        captured.append(entry)
        print(f'[RES] {response.status} {urlparse(url).path}')

    print('=' * 60)
    print('Jawwal Pay Network Capture')
    print('=' * 60)
    print(f'Opening: {START_URL}')
    print('1) Log in if prompted')
    print('2) Do: money transfer + SMS payment request')
    print('3) Return here and press ENTER to save and close')
    print('=' * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context_kwargs = {
            'locale': 'ar-PS',
            'viewport': {'width': 1400, 'height': 900},
            'user_agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
        }
        if STORAGE.exists():
            context_kwargs['storage_state'] = str(STORAGE)
            print(f'Reusing session: {STORAGE}')

        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.on('request', on_request)
        page.on('response', on_response)

        try:
            page.goto(START_URL, wait_until='domcontentloaded', timeout=120_000)
        except Exception as exc:
            print(f'Navigation note: {exc}')

        if args.auto_timeout > 0:
            print(f'Auto-capture for {args.auto_timeout}s — log in and run transfer + SMS payment now...')
            time.sleep(args.auto_timeout)
        else:
            input('\n>>> Press ENTER after finishing transfer + SMS payment request...\n')

        try:
            context.storage_state(path=str(STORAGE))
            print(f'Session saved: {STORAGE}')
        except Exception as exc:
            print(f'Could not save session: {exc}')

        browser.close()

    payload = {
        'captured_at': datetime.now(timezone.utc).isoformat(),
        'start_url': START_URL,
        'total_events': len(captured),
        'events': captured,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nSaved {len(captured)} events -> {OUTPUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
