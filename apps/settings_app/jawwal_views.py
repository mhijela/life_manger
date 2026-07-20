import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.finance.jawwal_pay_service import JawwalPayService
from apps.settings_app.models import SystemSettings

from .jawwal_forms import JawwalLoginForm, JawwalOtpForm


def _get_step(service: JawwalPayService) -> str:
    if service.is_authenticated():
        return 'done'
    if service.is_otp_pending():
        return 'otp'
    return 'login'


def _safe_json(data) -> str:
    if not data:
        return ''
    return json.dumps(data, ensure_ascii=False, indent=2)


@login_required
def jawwal_wizard(request):
    service = JawwalPayService()
    explicit_step = request.GET.get('step')
    if explicit_step:
        if explicit_step == 'login' and service.is_authenticated():
            step = 'done'
        elif explicit_step == 'login' and service.is_otp_pending():
            step = 'otp'
        else:
            step = explicit_step
    else:
        step = _get_step(service)
    api_debug = None
    otp_request_preview = None
    login_request_preview = service.build_login_request(
        SystemSettings.load().jawwal_username or 'user@serviceName',
        '********',
    )

    if request.method == 'POST':
        action = request.POST.get('wizard_action')

        if action == 'logout':
            service.clear_session()
            messages.info(request, 'تم مسح جلسة Jawwal Pay.')
            return redirect('settings_app:jawwal_wizard')

        elif action == 'relink':
            service.clear_session()
            sys_settings = SystemSettings.load()
            api_debug = service.login(
                sys_settings.jawwal_username,
                sys_settings.jawwal_password,
                force=True,
            )
            if api_debug.get('otp_required'):
                step = 'otp'
                otp_request_preview = api_debug.get('otp_request')
                messages.info(request, 'تم إرسال OTP — أدخل الرمز.')
            else:
                step = 'login'
                messages.error(request, api_debug.get('error', 'فشل إعادة الربط'))
            # fall through to render

        elif action == 'login':
            form = JawwalLoginForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                sys_settings = SystemSettings.load()
                sys_settings.jawwal_username = username
                sys_settings.jawwal_password = password
                sys_settings.save(update_fields=['jawwal_username', 'jawwal_password', 'updated_at'])

                relink = request.POST.get('force_relink') == '1'
                if not relink and service.is_authenticated():
                    step = 'done'
                    messages.success(request, 'الجلسة نشطة بالفعل — لا حاجة لإعادة تسجيل الدخول.')
                elif not relink and service.is_otp_pending():
                    step = 'otp'
                    otp_request_preview = service.get_session_info().get('otp_request')
                    messages.info(request, 'أكمل إدخال OTP — لا حاجة لتسجيل دخول جديد.')
                else:
                    api_debug = service.login(username, password, force=True)
                    login_request_preview = api_debug.get('request') or login_request_preview

                    if api_debug.get('otp_required'):
                        step = 'otp'
                        otp_request_preview = api_debug.get('otp_request')
                        messages.info(request, 'تم إرسال OTP — أدخل الرمز في الخطوة 2.')
                    elif api_debug.get('next_step') in ('done', 'payment') or service.is_authenticated():
                        step = 'done'
                        messages.success(request, 'تم تسجيل الدخول وحفظ الجلسة.')
                    else:
                        step = 'login'
                        messages.error(request, api_debug.get('error', 'فشل تسجيل الدخول'))
            else:
                step = 'login'

        elif action == 'otp':
            form = JawwalOtpForm(request.POST)
            if form.is_valid():
                api_debug = service.validate_otp(form.cleaned_data['otp'])
                otp_request_preview = api_debug.get('request')
                if api_debug.get('success') or service.is_authenticated():
                    step = 'done'
                    messages.success(request, api_debug.get('message', 'تم التحقق من OTP وحفظ الجلسة.'))
                else:
                    step = 'otp'
                    messages.error(request, api_debug.get('error', 'فشل التحقق من OTP'))
            else:
                step = 'otp'

    login_form = JawwalLoginForm(initial={'username': SystemSettings.load().jawwal_username})
    otp_form = JawwalOtpForm()
    session_info = service.get_session_info()
    if not otp_request_preview and session_info.get('otp_request'):
        otp_request_preview = session_info.get('otp_request')

    return render(request, 'settings_app/jawwal_wizard.html', {
        'step': step,
        'login_form': login_form,
        'otp_form': otp_form,
        'session_info': session_info,
        'session_json': _safe_json(session_info),
        'login_request_json': _safe_json(login_request_preview),
        'otp_request_json': _safe_json(otp_request_preview),
        'is_authenticated': service.is_authenticated(),
        'otp_pending': service.is_otp_pending(),
        'api_debug': _safe_json(api_debug),
        'finance_jawwal_url': reverse('finance:jawwal_payment'),
    })
