from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weighapp', '0006_weighingtransaction_paid_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='farmer',
            name='zone',
            field=models.CharField(choices=[('Zone A', 'Zone A '),
            ('Zone B', 'Zone B '), ('Zone C', 'Zone C ')], max_length=50),
        ),
    ]