
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weighapp', '0007_alter_farmer_zone'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='must_reset_password',
            field=models.BooleanField(default=False, help_text='If True, the user is forced to set a new password immediately after logging in — e.g. a newly created account, or an account whose password an administrator just reset.'),
        ),
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(choices=[('login', 'User Login'), ('logout', 'User Logout'), ('weight_entry', 'Weight Entry'), ('farmer_created', 'Farmer Created'), ('farmer_updated', 'Farmer Updated'), ('driver_created', 'Driver Created'), ('driver_updated', 'Driver Updated'), ('payment_marked', 'Driver Payment Marked'), ('password_self_reset', 'User Completed Mandatory Password Reset'), ('vehicle_created', 'Vehicle Created'), ('report_viewed', 'Report Viewed'), ('receipt_printed', 'Receipt Printed')], max_length=20),
        ),
    ]