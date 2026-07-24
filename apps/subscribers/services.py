from apps.messages.models import MessageTemplate
from apps.messages.services.sms_service import SMSService
from apps.settings_app.models import SystemSettings


def get_expiry_reminder_template():
    return MessageTemplate.objects.filter(
        template_type='expiry_reminder',
        is_active=True,
    ).first()


def build_expiry_reminder_context(subscriber, subscription=None):
    settings = SystemSettings.load()
    sub = subscription
    if sub is None:
        sub = (
            subscriber.active_subscription
            or subscriber.subscriptions.order_by('-end_date').first()
        )
    return {
        'name': subscriber.full_name,
        'phone': subscriber.phone,
        'company': settings.company_name,
        'expiry_date': sub.end_date if sub else '',
        'amount': sub.price if sub else (subscriber.monthly_price or ''),
        'due_date': sub.end_date if sub else '',
    }


def send_expiry_reminder_sms(subscriber):
    template = get_expiry_reminder_template()
    if not template:
        return None, 'لا يوجد قالب تذكير انتهاء اشتراك نشط في قوالب الرسائل'

    phone = (subscriber.phone or '').strip()
    if not phone:
        return None, 'المشترك لا يملك رقم هاتف'

    sms = SMSService()
    if not sms.is_configured():
        return None, 'إعدادات MTC SMS غير مكتملة'

    subscription = (
        subscriber.active_subscription
        or subscriber.subscriptions.order_by('-end_date').first()
    )
    context = build_expiry_reminder_context(subscriber, subscription)
    log = sms.send_template(phone, template, context)
    return log, None
