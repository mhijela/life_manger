# Jawwal Pay Flask API

API مستقل لتشغيل تدفق Jawwal Pay Business Portal — **متعدد المستخدمين**: كل تاجر له `api_key` وجلسة Jawwal منفصلة.

- إنشاء مستخدم API (تاجر) والحصول على `api_key` خاص به.
- تسجيل الدخول إلى Jawwal باسم المستخدم وكلمة المرور **لذلك التاجر فقط**.
- إدخال OTP مرة واحدة وحفظ الجلسة في مجلد خاص بالمستخدم.
- إنشاء طلب دفعة SMS لرقم ومبلغ.
- تأكيد طلب الدفعة برمز التحقق.
- استعلام سجل الدفعات المحلي بالتاريخ والوقت (معزول لكل مستخدم).
- استعلام صفحة تقارير البوابة بشكل best-effort.

> لا تحفظ كلمة مرور Jawwal في السيرفر. أرسلها فقط عند `POST /api/auth/login`. الـ `api_key` يحدد **أي حساب API** يُستخدم، والجلسة المحفوظة تربطه بحساب Jawwal بعد OTP.

## كيف يعمل التوثيق (Auth)

| الطبقة | ماذا تفعل |
|---|---|
| **Admin** | `ADMIN_TOKEN` يسمح بإنشاء مستخدمين API جدد |
| **مستخدم API** | `Authorization: Bearer <api_key>` يحدد التاجر — كل طلب يُوجَّه لجلسته وملفاته |
| **Jawwal** | `login` + `otp` يحفظان cookies في `data/users/<user_id>/jawwal_session.json` |

عندما يعود نفس التاجر لاحقاً ويرسل نفس `api_key`:

1. `GET /api/auth/status` — يقرأ جلسة **هذا المستخدم فقط**.
2. إذا الجلسة صالحة → الدفع يعمل بدون OTP جديد.
3. إذا انتهت → `login` ثم `otp` مرة أخرى **لنفس الـ api_key**.

مستخدمان مختلفان = `api_key` مختلف = مجلدات مختلفة — لا يختلطان.

## التشغيل

```powershell
cd "d:\سطح المكتب\CURSOR\life_manger\jawwal_pay_api"
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python app.py
```

الخدمة تعمل افتراضياً على:

```text
http://127.0.0.1:5000
```

## حماية الـ API

### Admin (إنشاء مستخدمين)

```powershell
$env:ADMIN_TOKEN = "change-me-admin-secret"
```

### مستخدم API (كل تاجر)

كل طلب Jawwal/Payments يحتاج:

```http
Authorization: Bearer <api_key_للتاجر>
```

## 0. إنشاء مستخدم (تاجر) — Admin فقط

```powershell
curl.exe -X POST http://127.0.0.1:5000/api/admin/users `
  -H "Authorization: Bearer change-me-admin-secret" `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Shop A\",\"user_id\":\"shop_a\"}"
```

الاستجابة تحتوي `api_key` — احفظه عند التاجر:

```json
{
  "success": true,
  "user": {
    "user_id": "shop_a",
    "name": "Shop A",
    "api_key": "xxxxxxxx"
  }
}
```

كرر العملية لتاجر ثانٍ (`shop_b`) — كل واحد يحصل على `api_key` مختلف.

## 1. فحص الخدمة

```powershell
curl.exe http://127.0.0.1:5000/health
```

## 2. تسجيل الدخول (لتاجر معيّن)

```powershell
curl.exe -X POST http://127.0.0.1:5000/api/auth/login `
  -H "Authorization: Bearer SHOP_A_API_KEY" `
  -H "Content-Type: application/json" `
  -d "{\"username\":\"admin@GZ09005\",\"password\":\"YOUR_PASSWORD\"}"
```

النتيجة المتوقعة أول مرة:

```json
{
  "success": true,
  "otp_required": true,
  "next_step": "otp"
}
```

## 3. إدخال OTP مرة واحدة

```powershell
curl.exe -X POST http://127.0.0.1:5000/api/auth/otp `
  -H "Authorization: Bearer SHOP_A_API_KEY" `
  -H "Content-Type: application/json" `
  -d "{\"otp\":\"12345\"}"
```

بعد النجاح تُحفظ الجلسة في:

```text
data/users/shop_a/jawwal_session.json
```

تاجر آخر (`shop_b`) يحفظ في `data/users/shop_b/...` — منفصل تماماً.

## 4. من أنا؟ + حالة الجلسة

```powershell
curl.exe http://127.0.0.1:5000/api/me `
  -H "Authorization: Bearer SHOP_A_API_KEY"
```

```powershell
curl.exe http://127.0.0.1:5000/api/auth/status `
  -H "Authorization: Bearer SHOP_A_API_KEY"
```

## 5. طلب دفعة

```powershell
curl.exe -X POST http://127.0.0.1:5000/api/payments/request `
  -H "Authorization: Bearer SHOP_A_API_KEY" `
  -H "Content-Type: application/json" `
  -d "{\"mobile\":\"0595108208\",\"amount\":\"1\"}"
```

الاستجابة تحتوي على `payment_id`:

```json
{
  "success": true,
  "payment_id": "uuid",
  "next_step": "confirm",
  "summary": {
    "mobile": "00970595108208",
    "amount": "1.0",
    "total_amount": "1.0",
    "otp_reference": "..."
  }
}
```

## 6. تأكيد الدفعة

```powershell
curl.exe -X POST http://127.0.0.1:5000/api/payments/<payment_id>/confirm `
  -H "Authorization: Bearer SHOP_A_API_KEY" `
  -H "Content-Type: application/json" `
  -d "{\"verification_code\":\"58080\"}"
```

إذا نجحت العملية، تُسجل في:

```text
data/users/shop_a/payments_history.json
```

## 7. الدفعات المعلقة

```powershell
curl.exe http://127.0.0.1:5000/api/payments/pending `
  -H "Authorization: Bearer SHOP_A_API_KEY"
```

## 8. استعلام الدفعات المحلية بالتاريخ والوقت

يعرض العمليات التي تمت عبر هذا الـ API:

```powershell
curl.exe "http://127.0.0.1:5000/api/payments?from=2026-07-13T00:00:00&to=2026-07-13T23:59:59" `
  -H "Authorization: Bearer SHOP_A_API_KEY"
```

فلترة الفشل/النجاح:

```powershell
curl.exe "http://127.0.0.1:5000/api/payments?status=success" `
  -H "Authorization: Bearer SHOP_A_API_KEY"
```

## 9. استعلام تقارير البوابة

يحاول قراءة صفحة تقارير Jawwal Pay نفسها:

```powershell
curl.exe "http://127.0.0.1:5000/api/payments/portal?from=13/07/2026&to=13/07/2026" `
  -H "Authorization: Bearer SHOP_A_API_KEY"
```

> هذا endpoint يعتمد على HTML صفحة التقارير في البوابة. إذا غيرت Jawwal Pay أسماء الحقول، قد نحتاج ضبط أسماء parameters.

## Endpoints

| Method | URL | الوصف |
|---|---|---|
| GET | `/health` | فحص الخدمة |
| POST | `/api/admin/users` | إنشاء مستخدم API (Admin) |
| GET | `/api/admin/users` | قائمة المستخدمين (Admin) |
| GET | `/api/me` | هوية المستخدم + حالة Jawwal |
| GET | `/api/auth/status` | حالة الجلسة |
| POST | `/api/auth/login` | تسجيل دخول username/password |
| POST | `/api/auth/otp` | إدخال OTP وحفظ الجلسة |
| DELETE | `/api/auth/session` | مسح الجلسة |
| POST | `/api/payments/request` | إنشاء طلب دفعة |
| POST | `/api/payments/<payment_id>/confirm` | تأكيد طلب الدفعة |
| GET | `/api/payments/pending` | الطلبات المعلقة |
| GET | `/api/payments` | سجل عمليات API |
| GET | `/api/payments/portal` | استعلام تقارير البوابة |

## هيكل التخزين

```text
data/users/
  registry.json              # user_id → api_key, name
  shop_a/
    jawwal_session.json      # cookies + authenticated state
    pending_payments.json
    payments_history.json
  shop_b/
    jawwal_session.json
    ...
```
