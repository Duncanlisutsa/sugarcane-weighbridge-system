from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Farmer, Vehicle, Driver, WeighingTransaction, AuditLog, TractorAllocation


# ─────────────────────────────────────────
# USER ADMIN
# ─────────────────────────────────────────
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ('username', 'full_name', 'role', 'is_active', 'must_reset_password')
    list_filter   = ('role', 'is_active', 'must_reset_password')
    search_fields = ('username', 'full_name')

    fieldsets = UserAdmin.fieldsets + (
        ('Role & Profile', {
            'fields': ('role', 'full_name', 'must_reset_password')
        }),
    )

    def save_model(self, request, obj, form, change):
        # Any account created here (Django's built-in admin), not just
        # through the app's own "Add User" screen, should still be
        # forced to set its own password on first login.
        if not change:
            obj.must_reset_password = True
        super().save_model(request, obj, form, change)


# ─────────────────────────────────────────
# FARMER ADMIN
# ─────────────────────────────────────────
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display  = ('farmer_code', 'full_name', 'phone', 'zone',
                     'next_of_kin_name', 'next_of_kin_phone',
                     'next_of_kin_relationship', 'created_at')
    search_fields = ('farmer_code', 'full_name', 'id_number', 'next_of_kin_name')
    list_filter   = ('zone',)


# ─────────────────────────────────────────
# DRIVER ADMIN
# ─────────────────────────────────────────
@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display  = ('driver_code', 'full_name', 'phone', 'id_number', 'created_at')
    search_fields = ('driver_code', 'full_name', 'id_number')


# ─────────────────────────────────────────
# VEHICLE ADMIN
# ─────────────────────────────────────────
@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display  = ('plate_number', 'make_model', 'created_at')
    search_fields = ('plate_number', 'make_model')


# ─────────────────────────────────────────
# TRACTOR ALLOCATION ADMIN
# ─────────────────────────────────────────
@admin.register(TractorAllocation)
class TractorAllocationAdmin(admin.ModelAdmin):
    list_display  = ('vehicle', 'farmer', 'driver', 'status', 'allocated_at', 'released_at')
    list_filter   = ('status',)
    search_fields = ('vehicle__plate_number', 'farmer__full_name', 'driver__full_name')


# ─────────────────────────────────────────
# WEIGHING TRANSACTION ADMIN
# ─────────────────────────────────────────
@admin.register(WeighingTransaction)
class WeighingTransactionAdmin(admin.ModelAdmin):
    list_display  = ('receipt_number', 'farmer', 'vehicle', 'driver',
                     'gross_weight_kg', 'tare_weight_kg',
                     'net_weight_kg', 'driver_earnings_kes',
                     'payment_status', 'status', 'gross_time')
    list_filter   = ('status', 'payment_status')
    search_fields = ('receipt_number', 'farmer__full_name', 'driver__full_name')
    readonly_fields = ('net_weight_kg', 'receipt_number')


# ─────────────────────────────────────────
# AUDIT LOG ADMIN
# ─────────────────────────────────────────
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ('logged_at', 'user', 'action', 'table_name', 'ip_address')
    list_filter   = ('action',)
    search_fields = ('user__full_name',)
    readonly_fields = ('user', 'action', 'table_name', 'record_id',
                       'old_value', 'new_value', 'ip_address', 'logged_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False