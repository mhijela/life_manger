from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_app', '0005_systemsettings_jawwal_mobile'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='auto_renew_enabled',
            field=models.BooleanField(default=True, verbose_name='تفعيل التجديد الشهري التلقائي'),
        ),
    ]
