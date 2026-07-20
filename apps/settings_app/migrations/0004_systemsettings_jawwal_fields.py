from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_app', '0003_systemsettings_debt_sms_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_base_url',
            field=models.URLField(blank=True, default='https://business.jawwalpay.ps', verbose_name='Jawwal Pay — رابط البوابة'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_field_map',
            field=models.TextField(blank=True, help_text='يُملأ تلقائياً بعد استيراد HAR', verbose_name='Jawwal — خريطة حقول API (JSON)'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_password',
            field=models.CharField(blank=True, max_length=255, verbose_name='Jawwal Pay — كلمة المرور'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_request_payment_url',
            field=models.CharField(blank=True, help_text='مثال: /merchant/requestPaymentServices — يُملأ تلقائياً من HAR', max_length=255, verbose_name='Jawwal — رابط طلب الدفعة (SMS)'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_session_path',
            field=models.CharField(blank=True, help_text='اختياري — لتخزين cookies الجلسة', max_length=500, verbose_name='Jawwal — مسار ملف الجلسة'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_transfer_url',
            field=models.CharField(blank=True, help_text='مثال: /merchant/transferMoneyServices — يُملأ تلقائياً من HAR', max_length=255, verbose_name='Jawwal — رابط تحويل الأموال'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_username',
            field=models.CharField(blank=True, max_length=150, verbose_name='Jawwal Pay — اسم المستخدم'),
        ),
    ]
