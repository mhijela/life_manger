from django.db import models


class SystemSettings(models.Model):
    company_name = models.CharField('اسم الشبكة', max_length=200, default='شبكة الإنترنت')
    logo = models.ImageField('الشعار', upload_to='logos/', blank=True, null=True)
    currency = models.CharField('العملة', max_length=10, default='ILS')
    currency_symbol = models.CharField('رمز العملة', max_length=10, default='₪')
    subscription_alert_days = models.PositiveIntegerField('أيام تنبيه انتهاء الاشتراك', default=3)
    pagination_size = models.PositiveIntegerField('عدد السجلات في الصفحة', default=20)
    timezone = models.CharField('المنطقة الزمنية', max_length=50, default='Asia/Gaza')
    sms_username = models.CharField('اسم مستخدم MTC SMS', max_length=100, blank=True)
    sms_api_key = models.CharField('كلمة مرور MTC SMS', max_length=255, blank=True)
    sms_sender_id = models.CharField('اسم المرسل (From)', max_length=50, blank=True)
    sms_api_url = models.URLField(
        'رابط إرسال SMS (اختياري)',
        blank=True,
        help_text='اتركه فارغاً لاستخدام الرابط الافتراضي: int.mtcsms.com',
    )
    cashbox_opening_balance = models.DecimalField(
        'رصيد الصندوق الافتتاحي', max_digits=12, decimal_places=2, default=0
    )
    auto_suspend_on_expiry = models.BooleanField('تعليق تلقائي عند الانتهاء', default=False)
    auto_renew_enabled = models.BooleanField('تفعيل التجديد الشهري التلقائي', default=True)
    debt_sms_template = models.ForeignKey(
        'inms_messages.MessageTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='قالب SMS تذكير الدين',
        help_text='يُستخدم عند إرسال تذكير دين من صفحة الديون',
    )
    jawwal_username = models.CharField('Jawwal Pay — اسم المستخدم', max_length=150, blank=True)
    jawwal_password = models.CharField('Jawwal Pay — كلمة المرور', max_length=255, blank=True)
    jawwal_base_url = models.URLField(
        'Jawwal Pay — رابط البوابة',
        blank=True,
        default='https://business.jawwalpay.ps',
    )
    jawwal_request_payment_url = models.CharField(
        'Jawwal — رابط طلب الدفعة (SMS)',
        max_length=255,
        blank=True,
        help_text='مثال: /merchant/requestPaymentServices — يُملأ تلقائياً من HAR',
    )
    jawwal_transfer_url = models.CharField(
        'Jawwal — رابط تحويل الأموال',
        max_length=255,
        blank=True,
        help_text='مثال: /merchant/transferMoneyServices — يُملأ تلقائياً من HAR',
    )
    jawwal_field_map = models.TextField(
        'Jawwal — خريطة حقول API (JSON)',
        blank=True,
        help_text='يُملأ تلقائياً بعد استيراد HAR',
    )
    jawwal_session_path = models.CharField(
        'Jawwal — مسار ملف الجلسة',
        max_length=500,
        blank=True,
        help_text='اختياري — لتخزين cookies الجلسة',
    )
    jawwal_mobile_api_base = models.URLField(
        'Jawwal Mobile API',
        blank=True,
        default='https://merchantsapi.jawwalpay.ps/mobileAPI/mobileAPI/',
    )
    jawwal_device_id = models.CharField('Jawwal — Device ID', max_length=64, blank=True)
    jawwal_mobile_session = models.TextField('Jawwal — جلسة Mobile API (JSON)', blank=True)
    jawwal_mobile_login_action = models.CharField(
        'Jawwal — login action',
        max_length=100,
        blank=True,
        default='login',
    )
    jawwal_mobile_otp_action = models.CharField(
        'Jawwal — OTP action',
        max_length=100,
        blank=True,
        default='validateTwoFactorAuth',
    )
    jawwal_mobile_payment_action = models.CharField(
        'Jawwal — payment SMS action',
        max_length=100,
        blank=True,
        default='requestPaymentViaSMS',
    )
    theme_primary = models.CharField(
        'اللون الأساسي',
        max_length=7,
        default='#6366f1',
        help_text='اللون العام للهوية (مثل #6366f1)',
    )
    theme_mode = models.CharField(
        'الوضع الافتراضي',
        max_length=10,
        choices=[
            ('system', 'حسب النظام'),
            ('light', 'فاتح'),
            ('dark', 'داكن'),
        ],
        default='system',
    )
    theme_radius = models.CharField(
        'استدارة العناصر',
        max_length=10,
        choices=[
            ('soft', 'ناعمة'),
            ('medium', 'متوسطة'),
            ('sharp', 'حادّة'),
        ],
        default='medium',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'إعدادات النظام'
        verbose_name_plural = 'إعدادات النظام'

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        from .theme import parse_hex
        self.pk = 1
        self.theme_primary = parse_hex(self.theme_primary)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def delete(self, *args, **kwargs):
        pass

    def get_theme_css_vars(self):
        from .theme import build_theme_vars
        return build_theme_vars(self.theme_primary, radius_style=self.theme_radius)
