"""Jawwal Pay Merchant Mobile API (merchantsapi.jawwalpay.ps)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from django.conf import settings as django_settings

from apps.settings_app.models import SystemSettings

MOBILE_API_BASE = 'https://merchantsapi.jawwalpay.ps/mobileAPI/mobileAPI/'
LOGIN_ACTION = 'login'
OTP_ACTION = 'validateTwoFactorAuth'
PAYMENT_SMS_ACTION = 'requestPaymentViaSMS'

MSG_CODE_LOGIN = 0
MSG_CODE_OTP = 1
MSG_CODE_PAYMENT = 2


class JawwalMobileService:
    def __init__(self):
        self.settings = SystemSettings.load()
        base = (self.settings.jawwal_mobile_api_base or MOBILE_API_BASE).strip()
        self.api_base = base if base.endswith('/') else f'{base}/'

    def _session_file(self) -> Path:
        return Path(django_settings.BASE_DIR) / 'tools' / 'jawwal_mobile_session.json'

    def load_session(self) -> dict:
        if self.settings.jawwal_mobile_session:
            try:
                return json.loads(self.settings.jawwal_mobile_session)
            except json.JSONDecodeError:
                pass
        path = self._session_file()
        if path.exists():
            try:
                return json.loads(path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                pass
        return {}

    def save_session(self, data: dict) -> None:
        merged = {**self.load_session(), **data}
        path = self._session_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')

        sys_settings = SystemSettings.load()
        sys_settings.jawwal_mobile_session = json.dumps(merged, ensure_ascii=False)
        sys_settings.save(update_fields=['jawwal_mobile_session', 'updated_at'])

    def get_device_id(self) -> str:
        session = self.load_session()
        if session.get('device_id'):
            return session['device_id']
        if self.settings.jawwal_device_id:
            return self.settings.jawwal_device_id
        device_id = str(uuid.uuid4()).upper()
        self.save_session({'device_id': device_id})
        return device_id

    def is_authenticated(self) -> bool:
        session = self.load_session()
        return bool(session.get('authenticated') and session.get('token'))

    def _build_envelope(
        self,
        body: dict,
        *,
        token: str = '',
        msg_code: int = 0,
        guid: str | None = None,
        signature: str = '',
    ) -> dict:
        device_id = self.get_device_id()
        request_guid = guid or str(uuid.uuid4())
        return {
            'header': {
                'token': token,
                'clientTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                'sender': device_id,
                'guid': request_guid,
                'msgCode': msg_code,
                'lang': 'ar',
                'osVersion': '8.1.0_O_MR1_sdk=27',
                'appVersion': '1.0.2',
                'spaceInMB': 0,
            },
            'body': {
                **body,
                'terminalSerial': device_id,
                'guid': request_guid,
            },
            'footer': {'signature': signature},
        }

    def _call(self, action: str, envelope: dict) -> dict:
        url = urljoin(self.api_base, action)
        device_id = self.get_device_id()
        headers = {
            'Content-Type': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'lang': 'ar',
            'sender': device_id,
            'Connection': 'keep-alive',
            'User-Agent': 'Dart/3.5 (dart:io)',
        }
        try:
            response = requests.post(url, json=envelope, headers=headers, timeout=45)
            raw_text = response.text
            try:
                parsed = response.json()
            except ValueError:
                parsed = {'raw': raw_text[:4000]}
            return {
                'success': response.ok,
                'status_code': response.status_code,
                'action': action,
                'url': url,
                'request': envelope,
                'response': parsed,
            }
        except requests.RequestException as exc:
            return {'success': False, 'error': str(exc), 'action': action, 'url': url}

    @staticmethod
    def _unwrap_response(api_result: dict) -> dict:
        response = api_result.get('response') or {}
        if isinstance(response, dict):
            body = response.get('body')
            if isinstance(body, dict):
                return body
            return response
        return {}

    def login(self, username: str, password: str) -> dict:
        username = username.strip()
        action = self.settings.jawwal_mobile_login_action or LOGIN_ACTION
        envelope = self._build_envelope(
            {'username': username, 'password': password},
            msg_code=MSG_CODE_LOGIN,
        )
        result = self._call(action, envelope)
        if not result.get('success') and result.get('status_code') == 404:
            for fallback in ('Login', 'merchantLogin', 'authenticate', 'authenticateUser'):
                if fallback == action:
                    continue
                envelope = self._build_envelope(
                    {'username': username, 'password': password},
                    msg_code=MSG_CODE_LOGIN,
                )
                result = self._call(fallback, envelope)
                if result.get('success') or result.get('status_code') != 404:
                    break

        body = self._unwrap_response(result)
        session_update = {'username': username}
        if body.get('token'):
            session_update['token'] = body['token']
        if body.get('otpRequestId') is not None:
            session_update['otp_request_id'] = body['otpRequestId']
            session_update['otp_required'] = True
        if body.get('otpRequired') is True:
            session_update['otp_required'] = True
        if session_update.keys() - {'username'}:
            self.save_session(session_update)

        result['otp_required'] = bool(session_update.get('otp_required'))
        result['next_step'] = 'otp' if result['otp_required'] else (
            'payment' if body.get('token') else 'login'
        )
        if body.get('token') and not result['otp_required']:
            self.save_session({'token': body['token'], 'authenticated': True, 'otp_required': False})
            result['next_step'] = 'payment'
        return result

    def validate_otp(self, otp: str) -> dict:
        session = self.load_session()
        username = session.get('username') or self.settings.jawwal_username
        token = session.get('token', '')
        otp_request_id = session.get('otp_request_id')

        if not username:
            return {'success': False, 'error': 'لا يوجد username — أعد خطوة تسجيل الدخول'}
        if otp_request_id is None:
            return {'success': False, 'error': 'لا يوجد otpRequestId — أعد خطوة تسجيل الدخول'}

        action = self.settings.jawwal_mobile_otp_action or OTP_ACTION
        envelope = self._build_envelope(
            {
                'username': username,
                'otp': str(otp).strip(),
                'otpRequestId': otp_request_id,
            },
            token=token,
            msg_code=MSG_CODE_OTP,
        )
        result = self._call(action, envelope)
        body = self._unwrap_response(result)

        if body.get('token'):
            self.save_session({
                'token': body['token'],
                'authenticated': True,
                'otp_required': False,
            })
            result['next_step'] = 'payment'
        else:
            result['next_step'] = 'otp' if not result.get('success') else 'login'

        return result

    def request_payment_sms(self, mobile: str, amount, note: str = '') -> dict:
        session = self.load_session()
        if not session.get('authenticated') or not session.get('token'):
            return {'success': False, 'error': 'يجب تسجيل الدخول أولاً', 'next_step': 'login'}

        action = self.settings.jawwal_mobile_payment_action or PAYMENT_SMS_ACTION
        phone = ''.join(c for c in str(mobile) if c.isdigit())
        if phone.startswith('970'):
            phone = phone[3:]
        if phone.startswith('0'):
            phone = phone[1:]

        envelope = self._build_envelope(
            {
                'mobileNumber': phone,
                'amount': str(amount),
                'description': note or '',
                'note': note or '',
            },
            token=session['token'],
            msg_code=MSG_CODE_PAYMENT,
        )
        result = self._call(action, envelope)
        if not result.get('success') and result.get('status_code') == 404:
            for fallback in (
                'requestPayment',
                'requestPaymentServices',
                'sendPaymentRequestSMS',
                'RequestPaymentViaSMS',
            ):
                result = self._call(fallback, envelope)
                if result.get('success') or result.get('status_code') != 404:
                    break

        result['next_step'] = 'payment'
        return result

    def clear_session(self) -> None:
        path = self._session_file()
        if path.exists():
            path.unlink(missing_ok=True)
        sys_settings = SystemSettings.load()
        sys_settings.jawwal_mobile_session = ''
        sys_settings.save(update_fields=['jawwal_mobile_session', 'updated_at'])
