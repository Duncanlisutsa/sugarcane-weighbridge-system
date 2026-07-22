# Generated manually to match auto-generated farmer_code (FC001, FC002, ...)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weighapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='farmer',
            name='farmer_code',
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
    ]