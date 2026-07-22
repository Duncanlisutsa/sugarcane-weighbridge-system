# Generated manually to add optional email field to Farmer

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weighapp', '0002_alter_farmer_farmer_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='farmer',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]