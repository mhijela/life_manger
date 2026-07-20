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
            [
                f for f in os.listdir(backup_dir)
                if f.endswith(('.sql', '.sql.gz', '.sqlite3'))
            ],
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


USER_TABLES = (
    'accounts_user',
    'accounts_userprofile',
    'accounts_user_groups',
    'accounts_user_user_permissions',
)


def _is_sqlite_file(path):
    try:
        with open(path, 'rb') as fh:
            return fh.read(16).startswith(b'SQLite format 3')
    except OSError:
        return False


def _decompress_backup_if_needed(filepath):
    """If upload is .gz, decompress to a sibling .sql and return that path."""
    if not filepath.endswith('.gz'):
        return filepath
    import gzip
    import shutil
    out_path = filepath[:-3] if filepath.endswith('.sql.gz') else (filepath[:-3] + '.sql')
    with gzip.open(filepath, 'rb') as src, open(out_path, 'wb') as dst:
        shutil.copyfileobj(src, dst)
    return out_path


def _snapshot_local_users():
    """Serialize current users so restore can keep Coolify/local login intact."""
    from django.core import serializers
    from apps.accounts.models import User, UserProfile

    users = list(User.objects.all().order_by('pk'))
    profiles = list(UserProfile.objects.all().order_by('pk'))
    return {
        'users': serializers.serialize('json', users),
        'profiles': serializers.serialize('json', profiles),
        'groups': {
            str(u.pk): list(u.groups.values_list('pk', flat=True)) for u in users
        },
        'permissions': {
            str(u.pk): list(u.user_permissions.values_list('pk', flat=True)) for u in users
        },
    }


def _restore_local_users(snapshot):
    from django.core import serializers
    from django.contrib.auth.models import Group, Permission
    from apps.accounts.models import User

    if not snapshot:
        return

    for obj in serializers.deserialize('json', snapshot['users']):
        obj.save()

    for obj in serializers.deserialize('json', snapshot['profiles']):
        obj.save()

    users_by_id = {str(u.pk): u for u in User.objects.all()}
    for pk, group_ids in snapshot.get('groups', {}).items():
        user = users_by_id.get(str(pk))
        if user:
            user.groups.set(Group.objects.filter(pk__in=group_ids))
    for pk, perm_ids in snapshot.get('permissions', {}).items():
        user = users_by_id.get(str(pk))
        if user:
            user.user_permissions.set(Permission.objects.filter(pk__in=perm_ids))


def _filter_sql_excluding_user_tables(src_path, dst_path):
    """Strip DROP/CREATE/COPY/INSERT for auth user tables from a pg_dump SQL file."""
    import re

    table_alt = '|'.join(re.escape(t) for t in USER_TABLES)
    copy_re = re.compile(
        rf'^COPY\s+(?:public\.)?(?:{table_alt})\b',
        re.IGNORECASE,
    )
    stmt_start_re = re.compile(
        rf'^(?:DROP\s+TABLE|CREATE\s+TABLE|ALTER\s+TABLE|INSERT\s+INTO|TRUNCATE)\s+'
        rf'(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?(?:public\.)?(?:{table_alt})\b',
        re.IGNORECASE,
    )
    setval_re = re.compile(
        rf"setval\s*\(\s*'[^']*(?:accounts_user_id_seq|accounts_userprofile_id_seq)",
        re.IGNORECASE,
    )

    # None | 'copy' | 'stmt'
    skipping = None
    with open(src_path, 'r', encoding='utf-8', errors='replace') as src, \
            open(dst_path, 'w', encoding='utf-8') as dst:
        for line in src:
            if skipping == 'copy':
                if line.strip() == r'\.':
                    skipping = None
                continue
            if skipping == 'stmt':
                if line.rstrip().endswith(';'):
                    skipping = None
                continue
            if copy_re.match(line):
                skipping = 'copy'
                continue
            if stmt_start_re.match(line):
                if not line.rstrip().endswith(';'):
                    skipping = 'stmt'
                continue
            if setval_re.search(line):
                continue
            dst.write(line)
    return dst_path


SQLITE_IMPORT_EXCLUDE = [
    'accounts.User',
    'accounts.UserProfile',
    'admin.LogEntry',
    'sessions.Session',
    'contenttypes',
    'auth.Permission',
    'auth.Group',
]


def _register_backup_sqlite_db(sqlite_path):
    """Attach an uploaded SQLite file as a temporary Django DB alias."""
    from django.db import connections

    alias = 'backup_src'
    connections.databases[alias] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': sqlite_path,
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': False,
        'OPTIONS': {},
        'TIME_ZONE': None,
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        'TEST': {
            'CHARSET': None,
            'COLLATION': None,
            'NAME': None,
            'MIRROR': None,
        },
    }
    if alias in connections:
        try:
            connections[alias].close()
        except Exception:
            pass
        del connections[alias]
    return alias


def _unregister_backup_sqlite_db(alias='backup_src'):
    from django.db import connections

    if alias in connections:
        try:
            connections[alias].close()
        except Exception:
            pass
        del connections[alias]
    connections.databases.pop(alias, None)


def _rewrite_user_fks_in_fixture(raw_json, fallback_user_id=None):
    """Point nullable user FKs at the current Coolify user (or null)."""
    import json

    objects = json.loads(raw_json or '[]')
    for obj in objects:
        fields = obj.get('fields') or {}
        if 'created_by' in fields:
            fields['created_by'] = fallback_user_id
        if obj.get('model') == 'accounts.userprofile':
            continue
    return json.dumps(objects)


def _import_sqlite_into_postgres(sqlite_path, fallback_user_id=None):
    """
    Migrate business data from a local SQLite backup into the current PostgreSQL DB.
    Users are intentionally excluded (caller restores the pre-import snapshot).
    """
    from io import StringIO
    from django.core.management import call_command

    alias = _register_backup_sqlite_db(sqlite_path)
    fixture_path = sqlite_path + '.fixture.json'
    try:
        buf = StringIO()
        call_command(
            'dumpdata',
            database=alias,
            exclude=SQLITE_IMPORT_EXCLUDE,
            natural_foreign=True,
            stdout=buf,
            verbosity=0,
        )
        fixture_json = _rewrite_user_fks_in_fixture(buf.getvalue(), fallback_user_id)
        with open(fixture_path, 'w', encoding='utf-8') as fh:
            fh.write(fixture_json)

        call_command('flush', interactive=False, database='default', verbosity=0)
        if fixture_json.strip() not in ('', '[]'):
            call_command('loaddata', fixture_path, database='default', verbosity=0)
    finally:
        _unregister_backup_sqlite_db(alias)
        try:
            os.remove(fixture_path)
        except OSError:
            pass


def _create_backup(request):
    backup_dir = settings.BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    db = settings.DATABASES['default']
    if db['ENGINE'] == 'django.db.backends.sqlite3':
        import shutil
        filename = f'backup_{timestamp}.sqlite3'
        filepath = os.path.join(backup_dir, filename)
        shutil.copy2(db['NAME'], filepath)
    else:
        filename = f'backup_{timestamp}.sql'
        filepath = os.path.join(backup_dir, filename)
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
            subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        except FileNotFoundError:
            messages.error(
                request,
                'فشل إنشاء النسخة الاحتياطية: أمر pg_dump غير موجود في السيرفر.',
            )
            return _redirect_with_tab(request, 'backup')
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or '').strip()
            messages.error(
                request,
                f'فشل إنشاء النسخة الاحتياطية{" — " + detail if detail else "."}',
            )
            return _redirect_with_tab(request, 'backup')

    return FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)


def _restore_backup(request):
    uploaded = request.FILES.get('backup_file')
    if not uploaded:
        messages.error(request, 'يرجى اختيار ملف النسخة الاحتياطية.')
        return _redirect_with_tab(request, 'backup')

    backup_dir = settings.BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)
    safe_name = os.path.basename(uploaded.name)
    filepath = os.path.join(backup_dir, safe_name)

    with open(filepath, 'wb+') as dest:
        for chunk in uploaded.chunks():
            dest.write(chunk)

    try:
        filepath = _decompress_backup_if_needed(filepath)
    except OSError:
        messages.error(request, 'تعذر فك ضغط ملف النسخة الاحتياطية.')
        return _redirect_with_tab(request, 'backup')

    users_snapshot = _snapshot_local_users()
    db = settings.DATABASES['default']

    if db['ENGINE'] == 'django.db.backends.sqlite3':
        if not _is_sqlite_file(filepath):
            messages.error(
                request,
                'الملف ليس نسخة SQLite صالحة. على اللوكل استخدم نسخة مأخوذة من نفس البيئة.',
            )
            return _redirect_with_tab(request, 'backup')
        import shutil
        from django.db import connections
        connections.close_all()
        shutil.copy2(filepath, db['NAME'])
        connections.close_all()
        _restore_local_users(users_snapshot)
        messages.success(request, 'تم استعادة النسخة الاحتياطية (مع الإبقاء على المستخدمين الحاليين).')
    else:
        if _is_sqlite_file(filepath):
            try:
                _import_sqlite_into_postgres(filepath, fallback_user_id=request.user.pk)
                _restore_local_users(users_snapshot)
                messages.success(
                    request,
                    'تم استيراد بيانات SQLite إلى PostgreSQL (مع الإبقاء على المستخدمين الحاليين).',
                )
            except Exception as exc:
                try:
                    _restore_local_users(users_snapshot)
                except Exception:
                    pass
                detail = str(exc).strip()
                if len(detail) > 300:
                    detail = detail[:300] + '…'
                messages.error(
                    request,
                    f'فشل استيراد ملف SQLite{" — " + detail if detail else "."}',
                )
            return _redirect_with_tab(request, 'backup')

        filtered_path = os.path.join(backup_dir, f'_restore_no_users_{os.path.basename(filepath)}')
        try:
            _filter_sql_excluding_user_tables(filepath, filtered_path)
        except OSError:
            messages.error(request, 'تعذر تجهيز ملف الاستعادة.')
            return _redirect_with_tab(request, 'backup')

        env = os.environ.copy()
        env['PGPASSWORD'] = db.get('PASSWORD', '')
        cmd = [
            'psql', '-h', db.get('HOST', 'localhost'),
            '-p', str(db.get('PORT', 5432)),
            '-U', db.get('USER', ''),
            '-d', db.get('NAME', ''),
            '-v', 'ON_ERROR_STOP=1',
            '-f', filtered_path,
        ]
        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
            _restore_local_users(users_snapshot)
            messages.success(request, 'تم استعادة النسخة الاحتياطية (مع الإبقاء على المستخدمين الحاليين).')
        except FileNotFoundError:
            messages.error(
                request,
                'فشل الاستعادة: أمر psql غير موجود. أعد نشر الصورة بعد تثبيت postgresql-client.',
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or '').strip()
            if len(detail) > 300:
                detail = detail[:300] + '…'
            messages.error(
                request,
                f'فشل استعادة النسخة الاحتياطية{" — " + detail if detail else "."}',
            )
        finally:
            try:
                os.remove(filtered_path)
            except OSError:
                pass

    return _redirect_with_tab(request, 'backup')
