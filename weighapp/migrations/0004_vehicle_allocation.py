# Generated manually: vehicle registration becomes independent of farmer;
# new TractorAllocation model tracks time-bound farmer<->vehicle assignment.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weighapp', '0003_farmer_email'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vehicle',
            name='farmer',
        ),
        migrations.CreateModel(
            name='TractorAllocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('allocated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('released_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('completed', 'Completed')], default='active', max_length=10)),
                ('allocated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='allocations_made', to=settings.AUTH_USER_MODEL)),
                ('farmer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='allocations', to='weighapp.farmer')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='allocations', to='weighapp.vehicle')),
            ],
            options={
                'ordering': ['-allocated_at'],
            },
        ),
    ]