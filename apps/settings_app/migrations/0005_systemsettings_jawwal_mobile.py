from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_app', '0004_systemsettings_jawwal_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_device_id',
            field=models.CharField(blank=True, max_length=64, verbose_name='Jawwal — Device ID'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_mobile_api_base',
            field=models.URLField(blank=True, default='https://merchantsapi.jawwalpay.ps/mobileAPI/mobileAPI/', verbose_name='Jawwal Mobile API'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_mobile_login_action',
            field=models.CharField(blank=True, default='login', max_length=100, verbose_name='Jawwal — login action'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_mobile_otp_action',
            field=models.CharField(blank=True, default='validateTwoFactorAuth', max_length=100, verbose_name='Jawwal — OTP action'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_mobile_payment_action',
            field=models.CharField(blank=True, default='requestPaymentViaSMS', max_length=100, verbose_name='Jawwal — payment SMS action'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='jawwal_mobile_session',
            field=models.TextField(blank=True, verbose_name='Jawwal — جلسة Mobile API (JSON)'),
        ),
    ]
