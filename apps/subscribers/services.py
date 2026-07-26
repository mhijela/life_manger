from decimal import Decimal

from apps.messages.models import MessageTemplate
from apps.messages.services.sms_service import SMSService
from apps.settings_app.models import SystemSettings


def get_expiry_reminder_template():
    return MessageTemplate.objects.filter(
        template_type='expiry_reminder',
        is_active=True,
    ).first()


def get_active_sms_templates():
    return MessageTemplate.objects.filter(is_active=True).order_by('template_type', 'name')


def build_expiry_reminder_context(subscriber, subscription=None):
    settings = SystemSettings.load()
    sub = subscription
    if sub is None:
        sub = (
            subscriber.active_subscription
            or subscriber.subscriptions.order_by('-end_date').first()
        )
    total_debt = sum(
        (d.remaining_amount for d in subscriber.debts.exclude(status='paid')),
        Decimal('0'),
    )
    return {
        'name': subscriber.full_name,
        'phone': subscriber.phone,
        'company': settings.company_name,
        'expiry_date': sub.end_date if sub else '',
        'amount': sub.price if sub else (subscriber.monthly_price or ''),
        'due_date': sub.end_date if sub else '',
        'total_amount': total_debt,
    }


def send_subscriber_sms(subscriber, template=None):
    """Send an SMS to a subscriber using the given template.

    Falls back to the active expiry-reminder template when none is given.
    """
    if template is None:
        template = get_expiry_reminder_template()
        if not template:
            return None, 'لا يوجد قالب تذكير انتهاء اشتراك نشط في قوالب الرسائل'
    elif not template.is_active:
        return None, 'القالب المحدد غير نشط'

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
