from apps.messages.models import MessageTemplate
from apps.messages.services.sms_service import SMSService
from apps.settings_app.models import SystemSettings


def get_debt_sms_template():
    settings = SystemSettings.load()
    if settings.debt_sms_template_id:
        return settings.debt_sms_template
    return MessageTemplate.objects.filter(
        template_type='debt_reminder',
        is_active=True,
    ).first()


def build_debt_sms_context(debt):
    settings = SystemSettings.load()
    subscriber = debt.subscriber
    return {
        'name': subscriber.full_name,
        'amount': debt.remaining_amount,
        'phone': subscriber.phone,
        'company': settings.company_name,
        'due_date': debt.due_date,
        'total_amount': debt.total_amount,
    }


def build_subscriber_debt_sms_context(subscriber):
    settings = SystemSettings.load()
    debts = list(subscriber.debts.exclude(status='paid'))
    earliest = min(debts, key=lambda d: d.due_date) if debts else None
    return {
        'name': subscriber.full_name,
        'amount': sum(d.remaining_amount for d in debts),
        'phone': subscriber.phone,
        'company': settings.company_name,
        'due_date': earliest.due_date if earliest else '',
        'total_amount': sum(d.total_amount for d in debts),
    }


def send_subscriber_debt_reminder_sms(subscriber):
    template = get_debt_sms_template()
    if not template:
        return None, 'لم يتم تحديد قالب تذكير الدين في الإعدادات'

    if not subscriber.debts.exclude(status='paid').exists():
        return None, 'لا يوجد دين مستحق'

    phone = subscriber.phone
    if not phone:
        return None, 'المشترك لا يملك رقم هاتف'

    sms = SMSService()
    if not sms.is_configured():
        return None, 'إعدادات MTC SMS غير مكتملة'

    context = build_subscriber_debt_sms_context(subscriber)
    log = sms.send_template(phone, template, context)
    return log, None


def get_debtor_subscribers():
    from apps.subscribers.models import Subscriber
    return Subscriber.objects.filter(
        debts__status__in=['pending', 'partial'],
    ).distinct().prefetch_related('debts')


def send_sms_to_all_debtors():
    sent = 0
    failed = 0
    skipped = 0
    errors = []

    template = get_debt_sms_template()
    if not template:
        return {'sent': 0, 'failed': 0, 'skipped': 0, 'total': 0, 'errors': ['لم يتم تحديد قالب تذكير الدين في الإعدادات']}

    sms = SMSService()
    if not sms.is_configured():
        return {'sent': 0, 'failed': 0, 'skipped': 0, 'total': 0, 'errors': ['إعدادات MTC SMS غير مكتملة']}

    subscribers = get_debtor_subscribers()
    total = subscribers.count()

    for subscriber in subscribers:
        log, error = send_subscriber_debt_reminder_sms(subscriber)
        if error:
            if 'لا يملك رقم هاتف' in error:
                skipped += 1
            else:
                failed += 1
            errors.append(f'{subscriber.full_name}: {error}')
        elif log and log.status == 'sent':
            sent += 1
        else:
            failed += 1
            errors.append(f'{subscriber.full_name}: {log.error_message if log else "فشل الإرسال"}')

    return {'sent': sent, 'failed': failed, 'skipped': skipped, 'total': total, 'errors': errors[:5]}


def _format_bulk_sms_result(result):
    if result['errors'] and not result['sent']:
        return 'error', result['errors'][0]
    msg = f'تم إرسال {result["sent"]} رسالة.'
    if result['failed']:
        msg += f' فشل {result["failed"]}.'
    if result['skipped']:
        msg += f' تم تخطي {result["skipped"]}.'
    return 'success', msg


def send_debt_reminder_sms(debt):
    template = get_debt_sms_template()
    if not template:
        return None, 'لم يتم تحديد قالب تذكير الدين في الإعدادات'

    phone = debt.subscriber.phone
    if not phone:
        return None, 'المشترك لا يملك رقم هاتف'

    sms = SMSService()
    if not sms.is_configured():
        return None, 'إعدادات MTC SMS غير مكتملة'

    context = build_debt_sms_context(debt)
    log = sms.send_template(phone, template, context)
    return log, None


def bulk_send_debt_reminders(debts):
    sent = 0
    failed = 0
    skipped = 0
    errors = []

    template = get_debt_sms_template()
    if not template:
        return {'sent': 0, 'failed': 0, 'skipped': 0, 'errors': ['لم يتم تحديد قالب تذكير الدين في الإعدادات']}

    sms = SMSService()
    if not sms.is_configured():
        return {'sent': 0, 'failed': 0, 'skipped': 0, 'errors': ['إعدادات MTC SMS غير مكتملة']}

    for debt in debts:
        if debt.status == 'paid':
            skipped += 1
            continue
        if not debt.subscriber.phone:
            skipped += 1
            errors.append(f'{debt.subscriber.full_name}: لا يوجد رقم هاتف')
            continue

        log, error = send_debt_reminder_sms(debt)
        if error:
            failed += 1
            errors.append(f'{debt.subscriber.full_name}: {error}')
        elif log and log.status == 'sent':
            sent += 1
        else:
            failed += 1
            errors.append(f'{debt.subscriber.full_name}: {log.error_message if log else "فشل الإرسال"}')

    return {'sent': sent, 'failed': failed, 'skipped': skipped, 'errors': errors[:5]}
