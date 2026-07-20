import requests
from django.utils import timezone
from apps.settings_app.models import SystemSettings
from apps.messages.models import MessageLog

MTC_SEND_URL = 'http://int.mtcsms.com/sendsms.aspx'
MTC_BALANCE_URL = 'http://api.mtcsms.com/balance.aspx'
MTC_SENDERS_URL = 'http://api.mtcsms.com/getSenders.aspx'

MTC_ERROR_CODES = {
    '0': 'تم إرسال الرسالة بنجاح',
    '10002': 'اسم المستخدم أو كلمة المرور غير صحيحة',
    '10003': 'حقل واحد أو أكثر فارغ',
    '10004': 'اسم المرسل غير مسموح',
    '10005': 'رصيد غير كافٍ',
    '10008': 'الحساب موقوف',
}


class SMSService:
    """MTC SMS API integration."""

    def __init__(self):
        self.settings = SystemSettings.load()

    def is_configured(self):
        return bool(
            self.settings.sms_username
            and self.settings.sms_api_key
            and self.settings.sms_sender_id
        )

    @staticmethod
    def _normalize_phone(phone):
        phone = str(phone).strip().replace(' ', '').replace('-', '')
        if phone.startswith('+'):
            phone = phone[1:]
        return phone

    @staticmethod
    def _parse_response(text):
        text = (text or '').strip()
        if '@' in text:
            code, message = text.split('@', 1)
            return code.strip(), message.strip()
        return text, text

    def _get_error_message(self, code, default=''):
        return MTC_ERROR_CODES.get(code, default or f'خطأ غير معروف ({code})')

    def _request(self, url, params):
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.text.strip()

    def send(self, phone, message, template=None, message_type=0):
        log = MessageLog.objects.create(
            template=template,
            recipient=phone,
            body=message,
            status='pending',
        )

        if not self.is_configured():
            log.status = 'failed'
            log.error_message = 'إعدادات MTC SMS غير مكتملة (اسم المستخدم، كلمة المرور، المرسل)'
            log.save()
            return log

        try:
            params = {
                'username': self.settings.sms_username,
                'password': self.settings.sms_api_key,
                'from': self.settings.sms_sender_id,
                'to': self._normalize_phone(phone),
                'msg': message,
                'type': message_type,
            }
            send_url = self.settings.sms_api_url or MTC_SEND_URL
            result = self._request(send_url, params)
            code, msg = self._parse_response(result)

            if code == '0':
                log.status = 'sent'
                log.sent_at = timezone.now()
            else:
                log.status = 'failed'
                log.error_message = self._get_error_message(code, msg)
        except requests.RequestException as e:
            log.status = 'failed'
            log.error_message = str(e)

        log.save()
        return log

    def send_template(self, phone, template, context):
        message = template.render(context)
        return self.send(phone, message, template=template)

    def check_balance(self):
        if not self.settings.sms_username or not self.settings.sms_api_key:
            return {'success': False, 'error': 'إعدادات MTC SMS غير مكتملة'}

        try:
            params = {
                'username': self.settings.sms_username,
                'password': self.settings.sms_api_key,
            }
            result = self._request(MTC_BALANCE_URL, params)
            code, msg = self._parse_response(result)

            if code == '0':
                return {'success': True, 'balance': msg}
            return {'success': False, 'error': self._get_error_message(code, msg)}
        except requests.RequestException as e:
            return {'success': False, 'error': str(e)}

    def get_senders(self):
        if not self.settings.sms_username or not self.settings.sms_api_key:
            return {'success': False, 'error': 'إعدادات MTC SMS غير مكتملة'}

        try:
            params = {
                'username': self.settings.sms_username,
                'password': self.settings.sms_api_key,
            }
            result = self._request(MTC_SENDERS_URL, params)
            code, msg = self._parse_response(result)

            if code == '0':
                senders = [s.strip() for s in msg.split(',') if s.strip()]
                return {'success': True, 'senders': senders}
            return {'success': False, 'error': self._get_error_message(code, msg)}
        except requests.RequestException as e:
            return {'success': False, 'error': str(e)}
