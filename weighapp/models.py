from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# ─────────────────────────────────────────
# TABLE 1: USERS
# Extends Django's built-in user system
# Adds a "role" field for access control
# ─────────────────────────────────────────
class User(AbstractUser):

    ROLE_CHOICES = [
        ('admin',   'Administrator'),
        ('manager', 'Manager'),
        ('clerk',   'Clerk'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='clerk'
    )

    full_name = models.CharField(max_length=150)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"


# ─────────────────────────────────────────
# TABLE 2: FARMERS
# Stores registered cane farmers
# ─────────────────────────────────────────
class Farmer(models.Model):

    farmer_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )
    full_name   = models.CharField(max_length=150)
    id_number   = models.CharField(max_length=20, unique=True)
    phone       = models.CharField(max_length=15)
    email       = models.EmailField(blank=True)
    zone        = models.CharField(max_length=50)

    next_of_kin_name         = models.CharField(max_length=150, default='')
    next_of_kin_phone        = models.CharField(max_length=15, default='')
    next_of_kin_relationship = models.CharField(max_length=50, default='')

    registered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='farmers_registered'
    )

    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.farmer_code:
            last_farmer = Farmer.objects.order_by('-id').first()
            if last_farmer and last_farmer.farmer_code[2:].isdigit():
                last_num = int(last_farmer.farmer_code[2:])
            else:
                last_num = 0
            self.farmer_code = f"FC{last_num + 1:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.farmer_code} - {self.full_name}"


# ─────────────────────────────────────────
# TABLE 3: VEHICLES
# Stores registered delivery vehicles
# ─────────────────────────────────────────
class Vehicle(models.Model):

    plate_number = models.CharField(
        max_length=20,
        unique=True
    )
    make_model = models.CharField(max_length=100)

    registered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='vehicles_registered'
    )

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.plate_number} - {self.make_model}"


# ─────────────────────────────────────────
# TABLE: TRACTOR ALLOCATIONS
# Tracks which vehicle is currently assigned
# to fetch cane for which farmer, and for how long
# ─────────────────────────────────────────
class TractorAllocation(models.Model):

    STATUS_CHOICES = [
        ('active',    'Active'),
        ('completed', 'Completed'),
    ]

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name='allocations'
    )

    farmer = models.ForeignKey(
        Farmer,
        on_delete=models.PROTECT,
        related_name='allocations'
    )

    allocated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='allocations_made'
    )

    allocated_at = models.DateTimeField(default=timezone.now)
    released_at  = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )

    class Meta:
        ordering = ['-allocated_at']

    @property
    def hours_elapsed(self):
        """Hours since allocation started (until now, or until release)."""
        end = self.released_at or timezone.now()
        return (end - self.allocated_at).total_seconds() / 3600

    @property
    def status_color(self):
        """green < 6hrs, orange 6-12hrs, red > 12hrs."""
        hours = self.hours_elapsed
        if hours < 6:
            return 'green'
        elif hours < 12:
            return 'orange'
        else:
            return 'red'

    def __str__(self):
        return f"{self.vehicle.plate_number} -> {self.farmer.full_name} ({self.status})"


# ─────────────────────────────────────────
# TABLE 4: WEIGHING TRANSACTIONS
# The core table — every weighing recorded
# ─────────────────────────────────────────
class WeighingTransaction(models.Model):

    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('complete', 'Complete'),
        ('voided',   'Voided'),
    ]

    farmer = models.ForeignKey(
        Farmer,
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    gross_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Full truck weight in kg"
    )

    tare_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Empty truck weight in kg"
    )

    net_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated automatically: gross minus tare"
    )

    gross_time = models.DateTimeField(default=timezone.now)
    tare_time  = models.DateTimeField(null=True, blank=True)

    clerk = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    receipt_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )

    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        # Auto-calculate net weight when tare is entered
        if self.gross_weight_kg and self.tare_weight_kg:
            self.net_weight_kg = self.gross_weight_kg - self.tare_weight_kg
            self.status = 'complete'

        # Auto-generate receipt number
        if not self.receipt_number:
            import datetime
            today = datetime.date.today()
            count = WeighingTransaction.objects.filter(
                gross_time__date=today
            ).count() + 1
            self.receipt_number = f"WB-{today.strftime('%Y%m%d')}-{count:04d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.receipt_number} | {self.farmer} | {self.net_weight_kg}kg"


# ─────────────────────────────────────────
# TABLE 5: AUDIT LOG
# Records every action in the system
# Cannot be edited or deleted
# ─────────────────────────────────────────
class AuditLog(models.Model):

    ACTION_CHOICES = [
        ('login',           'User Login'),
        ('logout',          'User Logout'),
        ('weight_entry',    'Weight Entry'),
        ('farmer_created',  'Farmer Created'),
        ('farmer_updated',  'Farmer Updated'),
        ('vehicle_created', 'Vehicle Created'),
        ('report_viewed',   'Report Viewed'),
        ('receipt_printed', 'Receipt Printed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )

    action     = models.CharField(max_length=20, choices=ACTION_CHOICES)
    table_name = models.CharField(max_length=50, blank=True)
    record_id  = models.IntegerField(null=True, blank=True)
    old_value  = models.TextField(blank=True)
    new_value  = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    logged_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-logged_at']

    def __str__(self):
        return f"{self.logged_at} | {self.user} | {self.action}"