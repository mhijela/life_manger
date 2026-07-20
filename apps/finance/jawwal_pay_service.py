"""Jawwal Pay Business Portal session client (business.jawwalpay.ps)."""
from __future__ import annotations

import json
import platform
import re
from datetime import datetime, timedelta
from http.cookiejar import Cookie
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings as django_settings

from apps.settings_app.models import SystemSettings

BASE_URL = 'https://business.jawwalpay.ps'
LOGIN_PAGE = '/login/auth'
LOGIN_POST = '/login/authenticate'
TWO_FACTOR_PAGE = '/login/twoFactorAuth'
TWO_FACTOR_POST = '/login/checkTwoFactorAuth'
MERCHANT_PAYMENT_PAGE = '/merchant/requestPaymentServices'
RECEIVE_PAYMENT_PAGE = '/merchant/receivePayment'
RECEIVE_PAYMENT_CONFIRM = '/merchant/confirmReceivePayment/receivePaymentForm'
SAVE_RECEIVE_PAYMENT = '/merchant/saveReceivePayment'
SESSION_TTL_HOURS = 24 * 30  # 30 days — match long-lived browser sessions
DEFAULT_SESSION_DIR = 'jawwal_sessions'
DEFAULT_SESSION_NAME = 'default.json'

try:
    from curl_cffi import requests as curl_requests

    _CURL_CFFI = True
except ImportError:
    curl_requests = None
    _CURL_CFFI = False

# Keeps the live portal session in memory within the same Django worker (avoids re-OTP on every request).
_LIVE_SESSION_PIN: dict[str, dict] = {}


def _create_http_session():
    if _CURL_CFFI:
        return curl_requests.Session(impersonate='chrome120')
    return requests.Session()


class JawwalPayError(Exception):
    pass


class JawwalPayService:
    """Automate Jawwal Pay merchant portal using an HTTP session."""

    def __init__(self):
        self.settings = SystemSettings.load()
        self.base_url = (self.settings.jawwal_base_url or BASE_URL).rstrip('/')
        self._session_state: dict = {}
        self._live_attached = False
        self.session = _create_http_session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'ar-PS,ar;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/json,application/xhtml+xml,*/*;q=0.8',
        })
        self._restore_session_from_file()
        self._try_attach_live_session()

    def is_configured(self) -> bool:
        return bool(self.settings.jawwal_username and self.settings.jawwal_password)

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        phone = re.sub(r'[\s\-+]', '', str(phone or ''))
        if phone.startswith('970'):
            phone = phone[3:]
        if phone.startswith('0'):
            phone = phone[1:]
        return phone

    @staticmethod
    def _build_fingerprint() -> str:
        parts = [
            '120',
            'Chrome',
            platform.system(),
            platform.release(),
            'false',
            'Asia/Gaza',
            'ar',
        ]
        return ''.join(parts).replace(' ', '')

    def _get_fingerprint(self) -> str:
        return self._session_state.get('fingerprint') or self._build_fingerprint()

    def _try_attach_live_session(self) -> bool:
        pin = _LIVE_SESSION_PIN.get('default')
        if not pin:
            return False
        data = self._read_session_file()
        pin_at = pin.get('authenticated_at')
        file_at = (data.get('state') or {}).get('authenticated_at')
        if not pin.get('authenticated') or not pin_at or pin_at != file_at:
            return False
        self.session = pin['session']
        self._session_state = dict(pin.get('state') or {})
        self._live_attached = True
        return True

    def _pin_live_session(self) -> None:
        if not self._session_state.get('authenticated'):
            return
        _LIVE_SESSION_PIN['default'] = {
            'session': self.session,
            'state': dict(self._session_state),
            'authenticated_at': self._session_state.get('authenticated_at'),
            'authenticated': True,
        }
        self._live_attached = True

    @staticmethod
    def _clear_live_session_pin() -> None:
        _LIVE_SESSION_PIN.pop('default', None)

    @staticmethod
    def _cookie_domain_candidates(domain: str, host: str) -> list[str]:
        domain = (domain or host).strip()
        bare = domain.lstrip('.')
        candidates = []
        for dom in (domain, bare, f'.{bare}' if bare else ''):
            if dom and dom not in candidates:
                candidates.append(dom)
        return candidates

    def _set_session_cookie(self, name: str, value: str, domain: str, path: str, secure: bool) -> None:
        jar = self.session.cookies
        if hasattr(jar, 'set_cookie'):
            for dom in self._cookie_domain_candidates(domain, urlparse(self.base_url).hostname or 'business.jawwalpay.ps'):
                try:
                    cookie = Cookie(
                        version=0,
                        name=name,
                        value=value,
                        port=None,
                        port_specified=False,
                        domain=dom,
                        domain_specified=True,
                        domain_initial_dot=dom.startswith('.'),
                        path=path,
                        path_specified=True,
                        secure=secure,
                        expires=None,
                        discard=False,
                        comment=None,
                        comment_url=None,
                        rest={},
                        rfc2109=False,
                    )
                    jar.set_cookie(cookie)
                    return
                except (TypeError, ValueError, AttributeError):
                    continue
            try:
                jar.set(name, value, domain=domain.lstrip('.'), path=path)
            except (TypeError, ValueError, AttributeError):
                pass
            return

        if hasattr(jar, 'set'):
            for dom in self._cookie_domain_candidates(domain, urlparse(self.base_url).hostname or 'business.jawwalpay.ps'):
                try:
                    jar.set(name, value, domain=dom.lstrip('.'), path=path, secure=secure)
                    return
                except (TypeError, ValueError, AttributeError):
                    continue

    def _apply_stored_cookies(self, cookies: list) -> None:
        self.session.cookies.clear()
        if not cookies:
            return
        host = urlparse(self.base_url).hostname or 'business.jawwalpay.ps'
        for item in cookies:
            name = item.get('name')
            value = item.get('value')
            if not name or value is None:
                continue
            domain = (item.get('domain') or host).strip()
            path = item.get('path') or '/'
            secure = bool(item.get('secure', True))
            self._set_session_cookie(name, value, domain, path, secure)

    def _build_cookie_header(self) -> str:
        """Merge jar + file cookies so cold restarts send the full saved snapshot."""
        pairs: dict[str, str] = {}
        for item in self._read_session_file().get('cookies', []):
            name = item.get('name')
            if name and item.get('value') is not None:
                pairs[name] = item['value']
        for name, value in self.session.cookies.get_dict().items():
            pairs[name] = value
        return '; '.join(f'{name}={value}' for name, value in pairs.items())

    def _portal_headers(self, extra: dict | None = None) -> dict:
        headers = dict(extra or {})
        cookie_header = self._build_cookie_header()
        if cookie_header:
            headers.setdefault('Cookie', cookie_header)
        return headers

    def _session_path(self) -> Path:
        custom = (self.settings.jawwal_session_path or '').strip()
        if custom:
            return Path(custom)
        tools_dir = Path(django_settings.BASE_DIR) / 'tools'
        new_path = tools_dir / DEFAULT_SESSION_DIR / DEFAULT_SESSION_NAME
        legacy_path = tools_dir / 'jawwal_session_cookies.json'
        if not new_path.exists() and legacy_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new_path.write_text(legacy_path.read_text(encoding='utf-8'), encoding='utf-8')
        return new_path

    def _restore_session_from_file(self) -> bool:
        data = self._read_session_file()
        if not data['cookies'] and not data.get('state'):
            self._session_state = {}
            return False
        if data['cookies']:
            self._apply_stored_cookies(data['cookies'])
        self._session_state = dict(data.get('state') or {})
        return bool(data['cookies'])

    def _read_session_file(self) -> dict:
        path = self._session_path()
        if not path.exists():
            return {'cookies': [], 'state': {}}
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return {'cookies': [], 'state': {}}
        if isinstance(data, list):
            return {'cookies': data, 'state': {}}
        return {
            'cookies': data.get('cookies', []),
            'state': data.get('state', {}),
        }

    def _load_session(self) -> bool:
        if self._live_attached and self._session_state.get('authenticated'):
            return bool(self.session.cookies)
        data = self._read_session_file()
        if not data['cookies'] and not data['state']:
            self._session_state = {}
            return False
        self._apply_stored_cookies(data['cookies'])
        self._session_state = data.get('state', {})
        return bool(data['cookies'])

    def _mark_authenticated(self) -> None:
        self._save_session({
            'authenticated': True,
            'otp_pending': False,
            'authenticated_at': datetime.now().isoformat(),
        })

    def _mark_session_expired(self, reason: str = '') -> None:
        """Portal rejected stored cookies — sync file state so UI does not show a false active session."""
        if not self._session_state.get('authenticated') and not self._read_session_file()['cookies']:
            return
        self._clear_live_session_pin()
        self._live_attached = False
        self._save_session({
            'authenticated': False,
            'otp_pending': False,
            'session_expired': True,
            'session_expired_at': datetime.now().isoformat(),
            'session_expired_reason': reason or 'portal_rejected_cookies',
        })

    def _session_is_fresh(self) -> bool:
        authenticated_at = self._session_state.get('authenticated_at')
        if not authenticated_at:
            return bool(self._session_state.get('authenticated'))
        try:
            at = datetime.fromisoformat(authenticated_at)
            return datetime.now() - at < timedelta(hours=SESSION_TTL_HOURS)
        except ValueError:
            return False

    def _export_session_cookies(self) -> list[dict]:
        exported: list[dict] = []
        seen: set[tuple[str, str, str]] = set()

        def add(name: str, value: str, domain: str | None, path: str | None,
                secure: bool = False, http_only: bool = False) -> None:
            if not name or value is None:
                return
            dom = (domain or 'business.jawwalpay.ps').strip()
            pth = path or '/'
            key = (name, dom.lstrip('.'), pth)
            if key in seen:
                return
            seen.add(key)
            exported.append({
                'name': name,
                'value': value,
                'domain': dom,
                'path': pth,
                'secure': secure,
                'httpOnly': http_only,
            })

        jar = getattr(self.session.cookies, 'jar', None)
        if jar is not None:
            for cookie in jar:
                rest = getattr(cookie, 'rest', {}) or {}
                add(
                    cookie.name,
                    cookie.value,
                    cookie.domain,
                    cookie.path,
                    secure=bool(getattr(cookie, 'secure', False)),
                    http_only='HttpOnly' in rest,
                )

        for stored in self._read_session_file().get('cookies', []):
            add(
                stored.get('name', ''),
                stored.get('value', ''),
                stored.get('domain'),
                stored.get('path'),
                secure=bool(stored.get('secure', False)),
                http_only=bool(stored.get('httpOnly', stored.get('http_only', False))),
            )

        for name, value in self.session.cookies.get_dict().items():
            add(name, value, 'business.jawwalpay.ps', '/')

        return exported

    def _persist_authenticated_session(self) -> bool:
        """Visit merchant pages and write a full cookie snapshot to disk."""
        warmed, _url = self._warm_authenticated_session()
        if warmed:
            self._mark_authenticated()
            return True
        if self._verify_merchant_access():
            self._mark_authenticated()
            return True
        return False

    def _save_session(self, state_update: dict | None = None) -> None:
        if state_update:
            self._session_state = {**self._session_state, **state_update}
        path = self._session_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        cookies = self._export_session_cookies()
        path.write_text(
            json.dumps({'cookies': cookies, 'state': self._session_state}, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        self._pin_live_session()

    def _url(self, path: str) -> str:
        if path.startswith('http'):
            return path
        return urljoin(f'{self.base_url}/', path.lstrip('/'))

    def _is_authenticated_html(self, html: str, url: str = '') -> bool:
        url_lower = (url or '').lower()
        if 'login/auth' in url_lower or 'twofactorauth' in url_lower:
            return False
        if '/merchant/' in url_lower or '/users/' in url_lower or '/branch/' in url_lower:
            return True
        if url_lower.rstrip('/').endswith('jawwalpay.ps') and 'login' not in url_lower:
            return True
        lower = (html or '').lower()
        if 'loginform' in lower and 'name="password"' in lower:
            return False
        if 'تسجيل دخول' in html and 'name="password"' in lower:
            return False
        if 'twofactorauth' in lower and 'name="password"' not in lower:
            return False
        return 'admin@' in html or 'requestpaymentservices' in lower or 'receivepayment' in lower

    def _needs_otp_html(self, html: str, url: str = '') -> bool:
        url_lower = (url or '').lower()
        if 'twofactorauth' in url_lower:
            return True
        lower = (html or '').lower()
        if 'twofactorauth' in lower:
            return True
        markers = ('otp', 'pin', 'رمز', 'two factor', 'twofactor', 'verification code')
        return any(m in lower for m in markers) and 'name="password"' not in lower

    def is_otp_pending(self) -> bool:
        self._load_session()
        return bool(self._session_state.get('otp_pending'))

    def discover_otp_request(self, html: str, page_url: str) -> dict:
        forms = self._parse_forms(html)
        otp_form = None
        for form in forms:
            blob = json.dumps(form, ensure_ascii=False).lower()
            if any(k in blob for k in ('otp', 'token', 'code', 'pin', 'رمز', 'verify')):
                otp_form = form
                break
        if not otp_form and forms:
            otp_form = forms[0]

        action = (otp_form or {}).get('action') or ''
        if not action:
            ajax_match = re.search(
                r'function\s+validateActivationCode\s*\(\)\s*\{.*?'
                r'var\s+url\s*=\s*["\']([^"\']+)["\']',
                html or '',
                re.S | re.I,
            )
            if ajax_match:
                action = ajax_match.group(1)
        if action and not action.startswith('http'):
            action = urljoin(page_url, action)
        if not action:
            action = self._url(TWO_FACTOR_POST)

        otp_field = 'otp'
        hidden_fields = {}
        for inp in (otp_form or {}).get('inputs', []):
            name = inp.get('name')
            if not name:
                continue
            field_type = inp.get('type', 'text')
            if field_type == 'hidden':
                hidden_fields[name] = inp.get('value', '')
            elif field_type in ('text', 'tel', 'number', 'password'):
                lower = name.lower()
                if any(k in lower for k in ('otp', 'code', 'token', 'pin', 'verify')):
                    otp_field = name

        post_path = urlparse(action).path if action.startswith('http') else action
        return {
            'method': (otp_form or {}).get('method') or 'POST',
            'url': action,
            'path': post_path or TWO_FACTOR_PAGE,
            'content_type': 'application/x-www-form-urlencoded',
            'otp_field': otp_field,
            'hidden_fields': hidden_fields,
        }

    def build_otp_request(self, otp: str, otp_spec: dict | None = None) -> dict:
        spec = otp_spec or self._session_state.get('otp_request') or {}
        path = spec.get('path') or TWO_FACTOR_PAGE
        otp_field = spec.get('otp_field') or 'otp'
        if path == TWO_FACTOR_PAGE and otp_field == 'activationCode':
            path = TWO_FACTOR_POST
        payload = {
            **(spec.get('hidden_fields') or {}),
            otp_field: str(otp).strip(),
            'trustedDevice': 'on',
        }
        return {
            'method': spec.get('method') or 'POST',
            'url': self._url(path),
            'path': path,
            'content_type': 'application/x-www-form-urlencoded',
            'payload': payload,
            'otp_field': otp_field,
        }

    def _restore_session_data(self, data: dict) -> None:
        self._apply_stored_cookies(data.get('cookies', []))
        self._session_state = dict(data.get('state') or {})

    @staticmethod
    def _is_auth_wall_url(url: str) -> bool:
        url_lower = (url or '').lower()
        return any(
            marker in url_lower
            for marker in ('/login/auth', '/login/authenticate', 'twofactorauth')
        )

    def _should_persist_cookies(self, response) -> bool:
        if self._is_auth_wall_url(response.url):
            return not self._session_state.get('authenticated')
        return True

    def _request(self, method: str, path: str, **kwargs):
        url = self._url(path)
        timeout = kwargs.pop('timeout', 45)
        headers = kwargs.pop('headers', None) or {}
        kwargs['headers'] = self._portal_headers(headers)
        response = self.session.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
        self.session.cookies.update(response.cookies)
        if self.session.cookies and self._should_persist_cookies(response):
            self._save_session()
        return response

    def _verify_merchant_access(self) -> bool:
        try:
            response = self.session.request(
                'GET',
                self._url(RECEIVE_PAYMENT_PAGE),
                allow_redirects=True,
                timeout=45,
                headers=self._portal_headers({'Referer': self._url(MERCHANT_PAYMENT_PAGE)}),
            )
            response.raise_for_status()
            self.session.cookies.update(response.cookies)
            if self._is_authenticated_html(response.text, response.url):
                self._save_session({'session_expired': False, 'session_expired_reason': ''})
                return True
        except requests.RequestException:
            pass
        return False

    def _warm_authenticated_session(self) -> tuple[bool, str]:
        """After OTP, visit merchant pages to capture fully-authenticated cookies."""
        headers = self._portal_headers({'Referer': self._url(TWO_FACTOR_PAGE)})
        for path in ('/', '/merchant/index', MERCHANT_PAYMENT_PAGE, RECEIVE_PAYMENT_PAGE):
            try:
                response = self.session.request(
                    'GET',
                    self._url(path),
                    allow_redirects=True,
                    timeout=45,
                    headers=headers,
                )
                response.raise_for_status()
                self.session.cookies.update(response.cookies)
                if self._is_authenticated_html(response.text, response.url):
                    self._save_session({'session_expired': False, 'session_expired_reason': ''})
                    return True, response.url
            except requests.RequestException:
                continue
        return False, ''

    def _cookie_names(self) -> list[str]:
        return sorted(self.session.cookies.get_dict().keys())

    def build_login_request(self, username: str, password: str) -> dict:
        return {
            'method': 'POST',
            'url': self._url(LOGIN_POST),
            'path': LOGIN_POST,
            'content_type': 'application/x-www-form-urlencoded',
            'payload': {
                'username': username.strip(),
                'password': password,
                'lang': 'ar_PS',
                'fingerprint': self._get_fingerprint(),
            },
        }

    @staticmethod
    def _parse_forms(html: str) -> list[dict]:
        forms = []
        form_pattern = r'<form(?P<attrs>[^>]*)>(?P<body>.*?)</form>'
        for match in re.finditer(form_pattern, html or '', re.S | re.I):
            attrs = match.group('attrs')
            block = match.group('body')
            action_m = re.search(r'action\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
            method_m = re.search(r'method\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
            inputs = []
            for tag in re.findall(r'<input[^>]+>', block, re.I):
                name_m = re.search(r'name=["\']([^"\']+)["\']', tag, re.I)
                if not name_m:
                    continue
                type_m = re.search(r'type=["\']([^"\']+)["\']', tag, re.I)
                value_m = re.search(r'value=["\']([^"\']*)["\']', tag, re.I)
                inputs.append({
                    'name': unescape(name_m.group(1)),
                    'type': (type_m.group(1) if type_m else 'text').lower(),
                    'value': unescape(value_m.group(1)) if value_m else '',
                })
            forms.append({
                'action': unescape(action_m.group(1)) if action_m else '',
                'method': (method_m.group(1) if method_m else 'GET').upper(),
                'inputs': inputs,
            })
        return forms

    @staticmethod
    def _extract_ajax_urls(html: str) -> list[str]:
        patterns = [
            r'url:\s*["\']([^"\']+)["\']',
            r'fetch\(["\']([^"\']+)["\']',
            r'\.post\(["\']([^"\']+)["\']',
        ]
        urls = []
        for pattern in patterns:
            urls.extend(re.findall(pattern, html or '', re.I))
        return list(dict.fromkeys(urls))

    def discover_payment_request(self, html: str, page_url: str) -> dict:
        forms = self._parse_forms(html)
        payment_form = None
        for form in forms:
            blob = json.dumps(form, ensure_ascii=False).lower()
            if any(k in blob for k in ('mobile', 'amount', 'msisdn', 'payment', 'phone', 'دفعة', 'مبلغ')):
                payment_form = form
                break
        if not payment_form and forms:
            payment_form = forms[0]

        action = (payment_form or {}).get('action') or MERCHANT_PAYMENT_PAGE
        if action and not action.startswith('http'):
            action = urljoin(page_url, action)

        field_names = [i['name'] for i in (payment_form or {}).get('inputs', []) if i.get('name')]
        ajax_urls = self._extract_ajax_urls(html)
        payment_ajax = [
            u for u in ajax_urls
            if any(k in u.lower() for k in ('payment', 'request', 'sms', 'merchant'))
        ]

        post_path = urlparse(action).path if action.startswith('http') else action
        return {
            'page_url': page_url,
            'method': (payment_form or {}).get('method') or 'POST',
            'url': action or self._url(MERCHANT_PAYMENT_PAGE),
            'path': post_path or MERCHANT_PAYMENT_PAGE,
            'form_fields': field_names,
            'hidden_defaults': {
                i['name']: i['value']
                for i in (payment_form or {}).get('inputs', [])
                if i.get('type') == 'hidden' and i.get('name')
            },
            'ajax_candidates': payment_ajax or ajax_urls[:10],
        }

    def _probe_merchant_access(self) -> tuple[bool, str]:
        if self._verify_merchant_access():
            return True, self._url(RECEIVE_PAYMENT_PAGE)
        return False, ''

    def _finalize_portal_session(self) -> bool:
        warmed, url = self._warm_authenticated_session()
        if warmed:
            return True
        return self._verify_merchant_access()

    def is_authenticated(self) -> bool:
        if (
            self._live_attached
            and self._session_state.get('authenticated')
            and not self._session_state.get('otp_pending')
            and self._session_is_fresh()
        ):
            return True

        self._load_session()
        if self._session_state.get('otp_pending'):
            return False
        if not self._read_session_file()['cookies']:
            return False
        if not self._session_state.get('authenticated') or not self._session_is_fresh():
            return False
        if self._verify_merchant_access():
            return True
        if self._warm_authenticated_session()[0]:
            self._mark_authenticated()
            return True
        self._mark_session_expired('merchant_probe_redirected_to_login')
        return False

    def ensure_merchant_session(self) -> dict:
        if self.is_authenticated():
            return {'success': True, 'message': 'الجلسة نشطة'}
        if self._session_state.get('otp_pending'):
            return {
                'success': False,
                'error': 'OTP مطلوب — أكمل الربط من الإعدادات',
                'next_step': 'otp',
            }
        had_saved_session = bool(self._read_session_file()['cookies'])
        if had_saved_session or self._session_state.get('session_expired'):
            return {
                'success': False,
                'error': 'انتهت جلسة Jawwal على البوابة — أعد تسجيل الدخول وOTP من الإعدادات',
                'next_step': 'login',
                'session_expired': True,
            }
        return {
            'success': False,
            'error': 'لا توجد جلسة Jawwal — اربط الحساب من الإعدادات',
            'next_step': 'login',
        }

    def get_session_info(self) -> dict:
        self._load_session()
        path = self._session_path()
        file_data = self._read_session_file()
        return {
            'session_file': str(path),
            'session_exists': path.exists(),
            'stored_cookie_count': len(file_data.get('cookies', [])),
            'cookie_names': self._cookie_names(),
            'authenticated': self.is_authenticated(),
            'authenticated_at': self._session_state.get('authenticated_at'),
            'otp_pending': self.is_otp_pending(),
            'otp_request': self._session_state.get('otp_request'),
            'login_request': self.build_login_request(
                self.settings.jawwal_username or '',
                '********',
            ),
            'payment_path': self.settings.jawwal_request_payment_url or MERCHANT_PAYMENT_PAGE,
        }

    def login(self, username: str | None = None, password: str | None = None, force: bool = False) -> dict:
        username = (username or self.settings.jawwal_username or '').strip()
        password = password if password is not None else self.settings.jawwal_password
        if not username or not password:
            return {'success': False, 'error': 'إعدادات Jawwal Pay غير مكتملة (اسم المستخدم وكلمة المرور)'}

        login_req = self.build_login_request(username, password)
        fingerprint = login_req['payload']['fingerprint']

        if not force and self._load_session():
            if self.is_authenticated():
                return {
                    'success': True,
                    'message': 'الجلسة الحالية صالحة',
                    'request': login_req,
                    'response': {'reused_session': True},
                    'cookies': self._cookie_names(),
                    'next_step': 'done',
                }
            if self._session_state.get('otp_pending'):
                return {
                    'success': False,
                    'error': 'أكمل OTP أولاً — لا حاجة لإعادة تسجيل الدخول',
                    'next_step': 'otp',
                }
            if self._read_session_file()['cookies']:
                return {
                    'success': False,
                    'error': 'انتهت جلسة Jawwal Pay — أعد OTP من الإعدادات',
                    'next_step': 'otp',
                    'session_expired': True,
                }

        if not force:
            return {
                'success': False,
                'error': 'لا توجد جلسة — سجّل الدخول من الإعدادات',
                'next_step': 'login',
            }

        try:
            self._request('GET', LOGIN_PAGE)
            response = self._request(
                'POST',
                LOGIN_POST,
                data=login_req['payload'],
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            return {'success': False, 'error': str(exc), 'request': login_req}

        otp_required = self._needs_otp_html(response.text, response.url)
        authenticated = self._is_authenticated_html(response.text, response.url) and not otp_required

        result = {
            'success': authenticated or otp_required,
            'request': login_req,
            'response': {
                'status_code': response.status_code,
                'final_url': response.url,
                'content_type': response.headers.get('content-type', ''),
                'preview': (response.text or '')[:2000],
            },
            'cookies': self._cookie_names(),
            'otp_required': otp_required,
            'next_step': 'otp' if otp_required else ('payment' if authenticated else 'login'),
        }

        if authenticated:
            self._mark_authenticated()
            result['message'] = 'تم تسجيل الدخول بنجاح'
            payment_spec = self.fetch_payment_request_spec()
            result['payment_request'] = payment_spec
        elif otp_required:
            otp_spec = self.discover_otp_request(response.text, response.url)
            otp_spec['method'] = 'POST'
            otp_spec['hidden_fields'] = {
                **(otp_spec.get('hidden_fields') or {}),
                'username': username,
                'fingerprint': login_req['payload']['fingerprint'],
            }
            self._save_session({
                'otp_pending': True,
                'authenticated': False,
                'otp_request': otp_spec,
                'fingerprint': fingerprint,
            })
            result['otp_request'] = otp_spec
            result['message'] = 'تم إرسال OTP — أدخل الرمز في الخطوة التالية'
        else:
            result['error'] = 'فشل تسجيل الدخول — تحقق من اسم المستخدم وكلمة المرور'

        return result

    def validate_otp(self, otp: str) -> dict:
        if not self._load_session():
            return {'success': False, 'error': 'لا توجد جلسة — أعد تسجيل الدخول', 'next_step': 'login'}

        if not self._session_state.get('otp_pending'):
            if self.is_authenticated():
                return {'success': True, 'message': 'الجلسة نشطة', 'next_step': 'payment'}
            return {'success': False, 'error': 'لا يوجد OTP معلّق — أعد تسجيل الدخول', 'next_step': 'login'}

        otp_spec = self._session_state.get('otp_request') or self.discover_otp_request('', self._url(TWO_FACTOR_PAGE))
        otp_req = self.build_otp_request(otp, otp_spec)
        post_paths = [otp_req['path']]
        for fallback in (
            TWO_FACTOR_POST,
            TWO_FACTOR_PAGE,
            '/login/validateTwoFactorAuth',
            '/login/verifyTwoFactorAuth',
        ):
            if fallback not in post_paths:
                post_paths.append(fallback)

        last_result = None
        for path in post_paths:
            payload = otp_req['payload']
            post_url = self._url(path)
            try:
                response = self.session.request(
                    'POST',
                    post_url,
                    data=payload,
                    allow_redirects=False,
                    timeout=45,
                    headers={
                        'Referer': self._url(TWO_FACTOR_PAGE),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                )
                response.raise_for_status()
                self.session.cookies.update(response.cookies)
            except requests.RequestException as exc:
                last_result = {
                    'success': False,
                    'error': str(exc),
                    'request': {**otp_req, 'path': path},
                    'next_step': 'otp',
                }
                continue

            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                try:
                    json_body = response.json()
                except ValueError:
                    json_body = {}
                accepted = bool(json_body.get('success')) and json_body.get('showInfo') is not True
                if accepted:
                    self._save_session({'otp_pending': False, 'trusted_device': True})
                    if self._persist_authenticated_session():
                        return {
                            'success': True,
                            'request': {**otp_req, 'path': path, 'url': self._url(path)},
                            'response': json_body,
                            'cookies': self._cookie_names(),
                            'next_step': 'done',
                            'message': 'تم التحقق من OTP وحفظ الجلسة في الملف',
                            'session_file': str(self._session_path()),
                        }
                    return {
                        'success': False,
                        'error': 'تم قبول OTP لكن فشل حفظ/التحقق من الجلسة على البوابة',
                        'next_step': 'otp',
                    }

                return {
                    'success': False,
                    'request': {**otp_req, 'path': path, 'url': self._url(path)},
                    'response': json_body,
                    'cookies': self._cookie_names(),
                    'next_step': 'otp',
                    'error': json_body.get('message') or 'فشل التحقق من OTP — تحقق من الرمز',
                }

            still_otp = self._needs_otp_html(response.text, response.url)
            authenticated = self._is_authenticated_html(response.text, response.url) and not still_otp
            if not authenticated and response.ok:
                try:
                    probe = self._request('GET', MERCHANT_PAYMENT_PAGE, allow_redirects=True)
                    authenticated = self._is_authenticated_html(probe.text, probe.url)
                    if authenticated:
                        response = probe
                except requests.RequestException:
                    pass

            result = {
                'success': authenticated,
                'request': {**otp_req, 'path': path, 'url': self._url(path)},
                'response': {
                    'status_code': response.status_code,
                    'final_url': response.url,
                    'content_type': response.headers.get('content-type', ''),
                    'preview': (response.text or '')[:2000],
                },
                'cookies': self._cookie_names(),
                'next_step': 'payment' if authenticated else 'otp',
            }

            if authenticated:
                self._persist_authenticated_session()
                result['message'] = 'تم التحقق من OTP وحفظ الجلسة في الملف'
                result['session_file'] = str(self._session_path())
                result['payment_request'] = self.fetch_payment_request_spec()
                return result

            last_result = result
            if response.status_code not in (404, 405):
                break

        if last_result:
            last_result['error'] = last_result.get('error') or 'فشل التحقق من OTP — تحقق من الرمز'
            return last_result
        return {'success': False, 'error': 'فشل التحقق من OTP', 'next_step': 'otp'}

    def fetch_payment_request_spec(self) -> dict:
        path = self.settings.jawwal_request_payment_url or MERCHANT_PAYMENT_PAGE
        try:
            response = self._request('GET', path, allow_redirects=True)
        except requests.RequestException as exc:
            return {'success': False, 'error': str(exc), 'path': path}

        if not self._is_authenticated_html(response.text, response.url):
            return {'success': False, 'error': 'غير مسجل دخول', 'path': path}

        spec = self.discover_payment_request(response.text, response.url)
        spec['success'] = True
        spec['get_request'] = {
            'method': 'GET',
            'url': response.url,
            'path': urlparse(response.url).path,
        }

        field_map = self._load_field_map()
        if spec.get('path') and not self.settings.jawwal_request_payment_url:
            sys_settings = SystemSettings.load()
            sys_settings.jawwal_request_payment_url = spec['path']
            sys_settings.save(update_fields=['jawwal_request_payment_url', 'updated_at'])

        if spec.get('form_fields') and not field_map.get('request_payment'):
            templates = {}
            for name in spec['form_fields']:
                lower = name.lower()
                if any(k in lower for k in ('mobile', 'msisdn', 'phone')):
                    templates[name] = '{mobile}'
                elif 'amount' in lower or 'value' in lower or 'مبلغ' in lower:
                    templates[name] = '{amount}'
                elif any(k in lower for k in ('note', 'desc', 'purpose', 'comment')):
                    templates[name] = '{note}'
            if templates:
                field_map['request_payment'] = templates
                sys_settings = SystemSettings.load()
                sys_settings.jawwal_field_map = json.dumps(field_map, ensure_ascii=False)
                sys_settings.save(update_fields=['jawwal_field_map', 'updated_at'])

        spec['field_map'] = field_map.get('request_payment', {})
        return spec

    def _ensure_logged_in(self) -> dict:
        return self.ensure_merchant_session()

    def _load_field_map(self) -> dict:
        if not self.settings.jawwal_field_map:
            return {'request_payment': {}, 'transfer': {}}
        try:
            data = json.loads(self.settings.jawwal_field_map)
            return data if isinstance(data, dict) else {'request_payment': {}, 'transfer': {}}
        except json.JSONDecodeError:
            return {'request_payment': {}, 'transfer': {}}

    def _post_merchant_action(self, path: str, payload: dict) -> dict:
        auth = self._ensure_logged_in()
        if not auth.get('success'):
            return auth

        post_url = self._url(path)
        try:
            response = self._request('POST', path, data=payload, allow_redirects=True)
        except requests.RequestException as exc:
            return {'success': False, 'error': str(exc), 'request': {'method': 'POST', 'url': post_url, 'payload': payload}}

        content_type = response.headers.get('content-type', '')
        body_text = response.text or ''
        request_debug = {
            'method': 'POST',
            'url': post_url,
            'path': path,
            'content_type': 'application/x-www-form-urlencoded',
            'payload': payload,
        }

        if 'application/json' in content_type:
            try:
                body = response.json()
            except ValueError:
                body = {'raw': body_text[:2000]}
            success = response.ok and body.get('success', True) is not False
            return {
                'success': success,
                'status_code': response.status_code,
                'request': request_debug,
                'response': body,
                'error': None if success else str(body),
                'next_step': 'payment',
            }

        success = response.ok and self._is_authenticated_html(body_text, response.url)
        error = None
        if 'alert-danger' in body_text or 'خطأ' in body_text:
            success = False
            error = 'رفض البوابة العملية — راجع الحقول أو رمز PIN/OTP'

        return {
            'success': success,
            'status_code': response.status_code,
            'request': request_debug,
            'response': {
                'final_url': response.url,
                'preview': body_text[:4000],
            },
            'error': error,
            'next_step': 'payment',
        }

    @staticmethod
    def _extract_form_values(form: dict) -> dict:
        return {
            inp['name']: inp.get('value', '')
            for inp in form.get('inputs', [])
            if inp.get('name')
        }

    @staticmethod
    def _parse_html_message(html: str) -> str | None:
        for pattern in (
            r'alert-danger[^>]*>.*?<button.*?</button>\s*(.*?)\s*<br',
            r'alert-success[^>]*>.*?<button.*?</button>\s*(.*?)\s*<br',
        ):
            match = re.search(pattern, html or '', re.S | re.I)
            if match:
                text = re.sub(r'<[^>]+>', '', match.group(1))
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    return text
        return None

    def _parse_receive_payment_result(self, html: str, submit_data: dict) -> dict:
        """Extract receipt-like details from portal response HTML."""
        message = self._parse_html_message(html)
        details = {
            'status': 'success',
            'status_label': 'نجح',
            'message': message or 'تم إرسال طلب الدفعة عبر SMS بنجاح',
            'mobile': submit_data.get('customerMobileNumber', ''),
            'amount': submit_data.get('amount', ''),
            'charges': submit_data.get('charges', '0'),
            'total_amount': submit_data.get('totalAmount', ''),
            'transaction_type': submit_data.get('transactionType', ''),
            'otp_reference': submit_data.get('otpReference', ''),
        }

        extra_fields: list[dict] = []
        seen: set[tuple[str, str]] = set()
        row_patterns = (
            r'<tr[^>]*>\s*<td[^>]*>\s*([^<]+?)\s*</td>\s*<td[^>]*>\s*([^<]+?)\s*</td>\s*</tr>',
            r'<dt[^>]*>\s*([^<]+?)\s*</dt>\s*<dd[^>]*>\s*([^<]+?)\s*</dd>',
            r'<label[^>]*>\s*([^<]+?)\s*</label>\s*(?:<[^>]+>\s*)?([^<]+?)\s*(?:</(?:span|div|p)>)',
        )
        for pattern in row_patterns:
            for raw_label, raw_value in re.findall(pattern, html or '', re.I | re.S):
                label = re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', '', raw_label))).strip(' :')
                value = re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', '', raw_value))).strip()
                if not label or not value or len(label) > 80:
                    continue
                key = (label, value)
                if key in seen:
                    continue
                seen.add(key)
                extra_fields.append({'label': label, 'value': value})

        details['extra_fields'] = extra_fields

        for pattern in (
            r'(?:رقم(?:\s)?(?:العملية|المرجع)|reference(?:No| Number)?)[^0-9A-Za-z]*([0-9]{6,})',
            r'transaction(?:Id|Reference)?["\']?\s*[:=]\s*["\']?([0-9A-Za-z-]{6,})',
        ):
            match = re.search(pattern, html or '', re.I)
            if match:
                details['transaction_reference'] = match.group(1)
                break

        return details

    def _format_customer_mobile(self, mobile: str) -> str:
        phone = self._normalize_phone(mobile)
        if phone and not phone.startswith('0'):
            phone = f'0{phone}'
        return phone

    def initiate_receive_payment(self, mobile: str, amount) -> dict:
        """Step 1: submit customer mobile + amount, return confirmation data for verification."""
        if not self.is_authenticated():
            auth = self._ensure_logged_in()
            if not auth.get('success'):
                return auth

        phone = self._format_customer_mobile(mobile)
        try:
            page = self._request('GET', RECEIVE_PAYMENT_PAGE, allow_redirects=True)
        except requests.RequestException as exc:
            return {'success': False, 'error': str(exc), 'next_step': 'login'}

        if self._is_auth_wall_url(page.url):
            return {
                'success': False,
                'error': 'انتهت جلسة Jawwal Pay — أعد OTP من الإعدادات',
                'next_step': 'otp',
            }

        if not self._is_authenticated_html(page.text, page.url):
            return {'success': False, 'error': 'انتهت جلسة Jawwal Pay — أعد تسجيل الدخول من الإعدادات', 'next_step': 'login'}

        forms = self._parse_forms(page.text)
        if not forms:
            return {'success': False, 'error': 'تعذر قراءة نموذج طلب الدفعة'}

        form = forms[0]
        payload = {
            **self._extract_form_values(form),
            'amount': str(amount),
            'customerMobileNumber': phone,
            'confirmMobileNumber': phone,
        }
        action = form.get('action') or RECEIVE_PAYMENT_CONFIRM

        try:
            response = self._request(
                'POST',
                action,
                data=payload,
                allow_redirects=True,
                headers={'Referer': self._url(RECEIVE_PAYMENT_PAGE)},
            )
        except requests.RequestException as exc:
            return {'success': False, 'error': str(exc)}

        body = response.text or ''
        if 'Request Rejected' in body:
            return {'success': False, 'error': 'رفضت البوابة الطلب — أعد تسجيل الدخول'}

        confirm_forms = self._parse_forms(body)
        if not confirm_forms:
            error = self._parse_html_message(body)
            return {'success': False, 'error': error or 'فشل إنشاء طلب الدفعة'}

        confirm_form = confirm_forms[0]
        confirm_data = self._extract_form_values(confirm_form)
        confirm_action = confirm_form.get('action') or SAVE_RECEIVE_PAYMENT

        return {
            'success': True,
            'next_step': 'verify',
            'confirm_action': confirm_action,
            'confirm_data': confirm_data,
            'summary': {
                'mobile': confirm_data.get('customerMobileNumber') or phone,
                'amount': confirm_data.get('amount') or str(amount),
                'total_amount': confirm_data.get('totalAmount') or str(amount),
                'otp_reference': confirm_data.get('otpReference', ''),
            },
            'message': 'تم إنشاء طلب الدفعة — أدخل رمز التحقق لإتمام العملية',
        }

    def confirm_receive_payment(self, verification_code: str, confirm_data: dict) -> dict:
        """Step 2: submit verification code to finalize SMS payment request."""
        if not self.is_authenticated():
            return {'success': False, 'error': 'انتهت الجلسة — أعد تسجيل الدخول من الإعدادات', 'next_step': 'login'}

        payload = {**confirm_data, 'verificationCode': str(verification_code).strip()}
        action = SAVE_RECEIVE_PAYMENT

        try:
            response = self._request(
                'POST',
                action,
                data=payload,
                allow_redirects=True,
                headers={'Referer': self._url(RECEIVE_PAYMENT_CONFIRM)},
            )
        except requests.RequestException as exc:
            return {'success': False, 'error': str(exc)}

        body = response.text or ''
        if 'Request Rejected' in body:
            return {'success': False, 'error': 'رفضت البوابة الطلب'}

        if 'alert-success' in body:
            details = self._parse_receive_payment_result(body, payload)
            return {
                'success': True,
                'message': details.get('message'),
                'details': details,
                'response': {'final_url': response.url},
            }

        error = self._parse_html_message(body)
        return {
            'success': False,
            'error': error or 'فشل إتمام طلب الدفعة — تحقق من رمز التحقق',
            'details': {
                'status': 'failed',
                'status_label': 'فشل',
                'message': error,
                'mobile': payload.get('customerMobileNumber', ''),
                'amount': payload.get('amount', ''),
                'total_amount': payload.get('totalAmount', ''),
                'otp_reference': payload.get('otpReference', ''),
            },
        }

    def request_payment_sms(self, mobile: str, amount, note: str = '') -> dict:
        """Request customer payment via SMS (merchant portal)."""
        return self.initiate_receive_payment(mobile, amount)

    def transfer_money(self, mobile: str, amount, note: str = '') -> dict:
        """Transfer money to a wallet number."""
        path = self.settings.jawwal_transfer_url or '/merchant/transferMoneyServices'
        payload = self._build_payload('transfer', mobile, amount, note)
        return self._post_merchant_action(path, payload)

    def _build_payload(self, action: str, mobile: str, amount, note: str) -> dict:
        phone = self._normalize_phone(mobile)
        amount_str = str(amount)

        mapping = self._load_field_map()
        action_map = mapping.get(action, {})
        if action_map:
            resolved = {}
            for key, template in action_map.items():
                resolved[key] = (
                    str(template)
                    .replace('{mobile}', phone)
                    .replace('{amount}', amount_str)
                    .replace('{note}', note or '')
                )
            return resolved

        return {
            'mobileNumber': phone,
            'mobile': phone,
            'msisdn': phone,
            'amount': amount_str,
            'description': note or '',
            'note': note or '',
            'purpose': note or '',
        }

    def clear_session(self) -> None:
        self._clear_live_session_pin()
        path = self._session_path()
        if path.exists():
            path.unlink(missing_ok=True)
        self.session.cookies.clear()
        self._session_state = {}
        self._live_attached = False
        self.session = _create_http_session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'ar-PS,ar;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/json,application/xhtml+xml,*/*;q=0.8',
        })

    @staticmethod
    def apply_har_discovery(discovery: dict) -> None:
        """Persist URLs/field map extracted from a HAR export."""
        sys_settings = SystemSettings.load()
        updates = []

        if discovery.get('login_post'):
            pass  # login path is fixed; payload fields stored in discovery file only
        if discovery.get('request_payment_url'):
            sys_settings.jawwal_request_payment_url = discovery['request_payment_url']
            updates.append('jawwal_request_payment_url')
        if discovery.get('transfer_url'):
            sys_settings.jawwal_transfer_url = discovery['transfer_url']
            updates.append('jawwal_transfer_url')
        if discovery.get('field_map'):
            sys_settings.jawwal_field_map = json.dumps(discovery['field_map'], ensure_ascii=False)
            updates.append('jawwal_field_map')

        if updates:
            sys_settings.save(update_fields=updates + ['updated_at'])
