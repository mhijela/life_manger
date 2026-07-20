from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='auto_renew',
            field=models.BooleanField(default=True, verbose_name='تجديد شهري تلقائياً'),
        ),
    ]
