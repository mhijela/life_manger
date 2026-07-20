from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse
from django.conf import settings
from django.urls import reverse
from django.db.models.deletion import ProtectedError
import os
import subprocess
from datetime import datetime
from .models import SystemSettings
from .forms import SystemSettingsForm
from apps.finance.forms import PaymentMethodForm
from apps.finance.models import PaymentMethod
from apps.messages.services.sms_service import SMSService
from apps.accounts.forms import AccountProfileForm, AccountPasswordForm
from django.contrib.auth import update_session_auth_hash
from apps.finance.jawwal_pay_service import JawwalPayService

VALID_TABS = {'account', 'general', 'finance', 'subscriptions', 'system', 'sms', 'jawwal', 'backup'}


def _redirect_with_tab(request, tab=None):
    tab = tab or request.POST.get('active_tab') or request.GET.get('tab', 'general')
    if tab not in VALID_TABS:
        tab = 'general'
    return redirect(f"{reverse('settings_app:index')}?tab={tab}")


@login_required
def index(request):
    sys_settings = SystemSettings.load()
    active_tab = request.GET.get('tab', 'general')
    if active_tab not in VALID_TABS:
        active_tab = 'general'

    form = SystemSettingsForm(instance=sys_settings)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'account_profile':
            profile_form = AccountProfileForm(request.user, request.POST)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'تم تحديث بيانات الحساب.')
            else:
                for err in profile_form.errors.values():
                    messages.error(request, err.as_text())
            return _redirect_with_tab(request, 'account')
        elif action == 'account_password':
            password_form = AccountPasswordForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'تم تغيير كلمة المرور بنجاح.')
            else:
                for err in password_form.errors.values():
                    messages.error(request, err.as_text())
            return _redirect_with_tab(request, 'account')
        elif action == 'settings':
            form = SystemSettingsForm(request.POST, request.FILES, instance=sys_settings)
            if form.is_valid():
                form.save()
                messages.success(request, 'تم حفظ الإعدادات.')
            else:
                messages.error(request, 'يرجى تصحيح الأخطاء في النموذج.')
            return _redirect_with_tab(request)
        elif action == 'backup':
            return _create_backup(request)
        elif action == 'restore':
            return _restore_backup(request)
        elif action == 'check_sms_balance':
            result = SMSService().check_balance()
            if result['success']:
                messages.success(request, f'رصيد SMS: {result["balance"]}')
            else:
                messages.error(request, result['error'])
            return _redirect_with_tab(request, 'sms')
        elif action == 'get_sms_senders':
            result = SMSService().get_senders()
            if result['success']:
                messages.info(request, f'المرسلون المسجلون: {", ".join(result["senders"])}')
            else:
                messages.error(request, result['error'])
            return _redirect_with_tab(request, 'sms')
        elif action == 'jawwal_login_test':
            service = JawwalPayService()
            if service.is_authenticated():
                messages.success(request, 'جلسة Jawwal Pay نشطة.')
            else:
                result = service.login(force=True)
                if result.get('otp_required'):
                    messages.info(request, 'OTP مطلوب — أكمل الربط من المعالج.')
                elif result.get('success'):
                    messages.success(request, result.get('message', 'تم الاتصال'))
                else:
                    messages.error(request, result.get('error', 'فشل الاتصال'))
            return _redirect_with_tab(request, 'jawwal')

    profile_form = AccountProfileForm(request.user)
    password_form = AccountPasswordForm(request.user)

    sms_service = SMSService()
    sms_balance = sms_service.check_balance() if sms_service.is_configured() else None
    jawwal_service = JawwalPayService()

    backups = []
    backup_dir = settings.BACKUP_DIR
    if os.path.exists(backup_dir):
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.endswith(('.sql', '.sql.gz'))],
            reverse=True,
        )

    return render(request, 'settings_app/index.html', {
        'form': form,
        'profile_form': profile_form,
        'password_form': password_form,
        'sys_settings': sys_settings,
        'backups': backups,
        'sms_balance': sms_balance,
        'sms_configured': sms_service.is_configured(),
        'jawwal_configured': jawwal_service.is_configured(),
        'active_tab': active_tab,
    })


@login_required
def payment_methods(request, pk=None):
    method = None
    if pk:
        from django.shortcuts import get_object_or_404
        method = get_object_or_404(PaymentMethod, pk=pk)

    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=method)
        if form.is_valid():
            saved_method = form.save()
            action = 'تحديث' if method else 'إضافة'
            messages.success(request, f'تم {action} طريقة الدفع «{saved_method.name}».')
            return redirect('settings_app:payment_methods')
    else:
        form = PaymentMethodForm(instance=method)

    return render(request, 'settings_app/payment_methods.html', {
        'form': form,
        'methods': PaymentMethod.objects.order_by('-is_active', 'name'),
        'editing_method': method,
    })


@login_required
def payment_method_toggle(request, pk):
    if request.method == 'POST':
        from django.shortcuts import get_object_or_404
        method = get_object_or_404(PaymentMethod, pk=pk)
        method.is_active = not method.is_active
        method.save(update_fields=['is_active'])
        messages.success(
            request,
            f'تم {"تفعيل" if method.is_active else "تعطيل"} طريقة الدفع «{method.name}».',
        )
    return redirect('settings_app:payment_methods')


@login_required
def payment_method_delete(request, pk):
    if request.method == 'POST':
        from django.shortcuts import get_object_or_404
        method = get_object_or_404(PaymentMethod, pk=pk)
        name = method.name
        try:
            method.delete()
            messages.success(request, f'تم حذف طريقة الدفع «{name}».')
        except ProtectedError:
            messages.error(
                request,
                f'لا يمكن حذف «{name}» لأنها مستخدمة في دفعات سابقة؛ يمكنك تعطيلها بدلاً من ذلك.',
            )
    return redirect('settings_app:payment_methods')


def _create_backup(request):
    backup_dir = settings.BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backup_{timestamp}.sql'
    filepath = os.path.join(backup_dir, filename)

    db = settings.DATABASES['default']
    if db['ENGINE'] == 'django.db.backends.sqlite3':
        import shutil
        shutil.copy2(db['NAME'], filepath)
    else:
        env = os.environ.copy()
        env['PGPASSWORD'] = db.get('PASSWORD', '')
        cmd = [
            'pg_dump', '-h', db.get('HOST', 'localhost'),
            '-p', str(db.get('PORT', 5432)),
            '-U', db.get('USER', ''),
            '-d', db.get('NAME', ''),
            '-f', filepath,
        ]
        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            messages.error(request, 'فشل إنشاء النسخة الاحتياطية. تأكد من تثبيت pg_dump.')
            return _redirect_with_tab(request, 'backup')

    return FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)


def _restore_backup(request):
    uploaded = request.FILES.get('backup_file')
    if not uploaded:
        messages.error(request, 'يرجى اختيار ملف النسخة الاحتياطية.')
        return _redirect_with_tab(request, 'backup')

    backup_dir = settings.BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)
    filepath = os.path.join(backup_dir, uploaded.name)

    with open(filepath, 'wb+') as dest:
        for chunk in uploaded.chunks():
            dest.write(chunk)

    db = settings.DATABASES['default']
    if db['ENGINE'] == 'django.db.backends.sqlite3':
        import shutil
        shutil.copy2(filepath, db['NAME'])
        messages.success(request, 'تم استعادة النسخة الاحتياطية.')
    else:
        env = os.environ.copy()
        env['PGPASSWORD'] = db.get('PASSWORD', '')
        cmd = [
            'psql', '-h', db.get('HOST', 'localhost'),
            '-p', str(db.get('PORT', 5432)),
            '-U', db.get('USER', ''),
            '-d', db.get('NAME', ''),
            '-f', filepath,
        ]
        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            messages.success(request, 'تم استعادة النسخة الاحتياطية.')
        except (subprocess.CalledProcessError, FileNotFoundError):
            messages.error(request, 'فشل استعادة النسخة الاحتياطية.')

    return _redirect_with_tab(request, 'backup')
