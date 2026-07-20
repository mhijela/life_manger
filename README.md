# نظام إدارة شبكة الإنترنت (INMS)

نظام ويب متكامل لإدارة شبكات الإنترنت الخاصة، مبني بـ Django 5 مع واجهة عربية RTL.

## المميزات

- إدارة المشتركين والاشتراكات والباقات
- إدارة مالية (دفعات، مصروفات، ديون، صندوق)
- إدارة المخزون والأصول والأجهزة الشبكية
- إرسال رسائل SMS عبر API قابل للتخصيص
- تقارير شاملة مع تصدير Excel و PDF
- نسخ احتياطي واستعادة قاعدة البيانات
- مهام مجدولة عبر Celery (تنبيهات انتهاء الاشتراك، المخزون)
- واجهة عربية RTL مع Bootstrap 5

## المتطلبات

- Python 3.12+
- PostgreSQL 16 (أو SQLite للتطوير المحلي)
- Redis (للمهام المجدولة)

## التثبيت المحلي

```bash
# إنشاء بيئة افتراضية
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate     # Linux/Mac

# تثبيت المتطلبات
pip install -r requirements.txt

# نسخ ملف البيئة
copy .env.example .env         # Windows

# تشغيل الهجرات
python manage.py migrate

# تحميل بيانات تجريبية
python manage.py load_demo_data

# تشغيل السيرفر
python manage.py runserver
```

**بيانات الدخول التجريبية:**
- البريد: `admin@inms.local`
- كلمة المرور: `admin123`

## التشغيل بـ Docker

```bash
docker-compose up --build
```

يفتح النظام على: http://localhost:8000

```bash
# تحميل بيانات تجريبية داخل الحاوية
docker-compose exec web python manage.py load_demo_data
```

## النشر على Coolify

المشروع جاهز لـ **Docker Compose** على Coolify.

### 1) في Coolify
1. New Resource → **Docker Compose**
2. اربط مستودع Git (أو ارفع الملفات)
3. تأكد أن ملف التركيب هو `docker-compose.yml`
4. عيّن المتغيرات التالية في Environment:

| المتغير | مثال |
|---------|------|
| `SECRET_KEY` | مفتاح عشوائي طويل |
| `POSTGRES_PASSWORD` | كلمة مرور قوية لقاعدة البيانات |
| `ALLOWED_HOSTS` | `your-domain.com,www.your-domain.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://your-domain.com,https://www.your-domain.com` |
| `DEBUG` | `False` |
| `POSTGRES_DB` | `inms` (اختياري) |
| `POSTGRES_USER` | `inms` (اختياري) |

5. فعّل **HTTPS** / Let's Encrypt على النطاق
6. Deploy

### 2) بعد أول نشر — إنشاء مدير النظام
من Terminal داخل حاوية `web`:

```bash
python manage.py createsuperuser
```

أو:

```bash
python manage.py shell -c "from apps.accounts.models import User; User.objects.create_superuser(email='admin@inms.local', password='admin123', first_name='Admin')"
```

(عدّل الإيميل وكلمة المرور قبل الإنتاج)

### 3) ملاحظات
- Volume `media_data` يحفظ الشعارات والنسخ الاحتياطية
- الخدمات: `web` + `db` + `redis` + `celery` + `celery-beat`
- الترحيلات و`collectstatic` تعمل تلقائياً عند إقلاع `web`
- لا تستخدم SQLite على Coolify — PostgreSQL مضمّن في الـ compose

### 4) إن أردت PostgreSQL/Redis من Coolify بدل الحاويات
احذف خدمات `db`/`redis` من الـ compose (أو عطّلها) وضَع:

```
DATABASE_URL=postgres://user:pass@host:5432/dbname
CELERY_BROKER_URL=redis://host:6379/0
```

## هيكل التطبيقات

| التطبيق | الوظيفة |
|---------|---------|
| accounts | المستخدمون وتسجيل الدخول |
| dashboard | لوحة التحكم والإحصائيات |
| subscribers | إدارة المشتركين |
| subscriptions | الباقات والاشتراكات |
| finance | الدفعات والمصروفات والديون |
| inventory | المخزون وحركاته |
| assets | الأصول المُسلّمة |
| devices | الأجهزة الشبكية |
| messages | الرسائل وقوالب SMS |
| reports | التقارير والتصدير |
| settings_app | إعدادات النظام والنسخ الاحتياطي |

## إعداد MTC SMS

من صفحة **الإعدادات > MTC SMS**، أدخل:
- **اسم المستخدم** (Username)
- **كلمة المرور** (Password)
- **اسم المرسل** (From / Sender)

### روابط API المستخدمة

| الوظيفة | الرابط |
|---------|--------|
| إرسال رسالة | `http://int.mtcsms.com/sendsms.aspx` |
| فحص الرصيد | `http://api.mtcsms.com/balance.aspx` |
| قائمة المرسلين | `http://api.mtcsms.com/getSenders.aspx` |

### معاملات الإرسال

```
username, password, from, to, msg, type
```

- `type=0` — رسالة عادية (عربي/إنجليزي UTF)
- `type=1` — HexCode

### أكواد الاستجابة

| الكود | المعنى |
|-------|--------|
| 0 | تم الإرسال بنجاح |
| 10002 | اسم مستخدم/كلمة مرور خاطئة |
| 10003 | حقل فارغ |
| 10004 | اسم مرسل غير مسموح |
| 10005 | رصيد غير كافٍ |
| 10008 | الحساب موقوف |

## التوسع المستقبلي

النظام مُجهّز لتكامل:
- **MikroTik API** - حقول IP/MAC/PPPoE على المشتركين والأجهزة
- **WhatsApp/Telegram** - حقل `channel` في قوالب الرسائل
- **تطبيق موبايل** - هيكل apps منفصل جاهز لإضافة Django REST Framework
- **Hotspot/PPPoE** - حقل `pppoe_username` على المشترك
- **تعليق تلقائي** - إعداد `auto_suspend_on_expiry` + Celery task
- **GPS للمناطق** - حقول `latitude/longitude` على جدول المناطق

## الأوامر المفيدة

```bash
python manage.py migrate              # تطبيق الهجرات
python manage.py load_demo_data       # بيانات تجريبية
python manage.py createsuperuser      # إنشاء مدير
python manage.py collectstatic        # جمع الملفات الثابتة
celery -A config worker -l info       # تشغيل Celery worker
celery -A config beat -l info         # تشغيل المجدول
```

## الترخيص

مشروع خاص - جميع الحقوق محفوظة.
