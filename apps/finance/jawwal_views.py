from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.finance.jawwal_forms import JawwalPaymentRequestForm, JawwalVerificationForm
from apps.finance.jawwal_pay_service import JawwalPayService

SESSION_KEY = 'jawwal_payment_pending'
RESULT_KEY = 'jawwal_payment_result'


@login_required
def jawwal_payment_request(request):
    service = JawwalPayService()

    session_result = service.ensure_merchant_session()
    if not session_result.get('success'):
        if session_result.get('next_step') == 'otp':
            messages.warning(request, 'أكمل إدخال OTP من إعدادات Jawwal Pay.')
        elif session_result.get('session_expired'):
            messages.warning(
                request,
                'انتهت جلسة Jawwal على البوابة (ال cookies المحفوظة لم تعد مقبولة) — أعد تسجيل الدخول وOTP من الإعدادات.',
            )
        else:
            messages.warning(
                request,
                'يجب ربط Jawwal Pay أولاً من الإعدادات (تسجيل الدخول + OTP).',
            )
        return redirect(f"{reverse('settings_app:jawwal_wizard')}")

    if request.method == 'POST':
        form = JawwalPaymentRequestForm(request.POST)
        if form.is_valid():
            result = service.initiate_receive_payment(
                form.cleaned_data['mobile'],
                form.cleaned_data['amount'],
            )
            if result.get('success'):
                request.session[SESSION_KEY] = {
                    'confirm_action': result.get('confirm_action'),
                    'confirm_data': result.get('confirm_data'),
                    'summary': result.get('summary'),
                }
                request.session.modified = True
                messages.info(request, result.get('message', 'أدخل رمز التحقق لإتمام العملية.'))
                return redirect('finance:jawwal_payment_verify')
            messages.error(request, result.get('error', 'فشل إنشاء طلب الدفعة'))
    else:
        form = JawwalPaymentRequestForm()

    return render(request, 'finance/jawwal_payment_request.html', {
        'form': form,
        'is_connected': True,
    })


@login_required
def jawwal_payment_verify(request):
    service = JawwalPayService()
    pending = request.session.get(SESSION_KEY)

    if not pending:
        messages.warning(request, 'لا يوجد طلب دفعة معلّق.')
        return redirect('finance:jawwal_payment')

    if not service.ensure_merchant_session().get('success'):
        messages.warning(request, 'انتهت جلسة Jawwal Pay — أعد الربط من الإعدادات.')
        return redirect(f"{reverse('settings_app:jawwal_wizard')}")

    summary = pending.get('summary', {})

    if request.method == 'POST':
        form = JawwalVerificationForm(request.POST)
        if form.is_valid():
            result = service.confirm_receive_payment(
                form.cleaned_data['verification_code'],
                pending.get('confirm_data', {}),
            )
            if result.get('success'):
                del request.session[SESSION_KEY]
                request.session.modified = True
                return render(request, 'finance/jawwal_payment_success.html', {
                    'details': result.get('details') or {},
                    'success': True,
                })
            messages.error(request, result.get('error', 'فشل إتمام طلب الدفعة'))
    else:
        form = JawwalVerificationForm()

    return render(request, 'finance/jawwal_payment_verify.html', {
        'form': form,
        'summary': summary,
    })


@login_required
def jawwal_payment_success(request):
    details = request.session.pop(RESULT_KEY, None)
    if not details:
        messages.info(request, 'لا توجد عملية حديثة لعرضها.')
        return redirect('finance:jawwal_payment')

    request.session.modified = True
    return render(request, 'finance/jawwal_payment_success.html', {
        'details': details,
        'success': details.get('status') == 'success',
    })
