from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Farmer, Vehicle, WeighingTransaction, AuditLog


# ─────────────────────────────────────────
# USER ADMIN
# ─────────────────────────────────────────
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ('username', 'full_name', 'role', 'is_active')
    list_filter   = ('role', 'is_active')
    search_fields = ('username', 'full_name')

    fieldsets = UserAdmin.fieldsets + (
        ('Role & Profile', {
            'fields': ('role', 'full_name')
        }),
    )


# ─────────────────────────────────────────
# FARMER ADMIN
# ─────────────────────────────────────────
@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display  = ('farmer_code', 'full_name', 'phone', 'zone', 'created_at')
    search_fields = ('farmer_code', 'full_name', 'id_number')
    list_filter   = ('zone',)


# ─────────────────────────────────────────
# VEHICLE ADMIN
# ─────────────────────────────────────────
@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display  = ('plate_number', 'make_model', 'farmer', 'created_at')
    search_fields = ('plate_number', 'make_model')


# ─────────────────────────────────────────
# WEIGHING TRANSACTION ADMIN
# ─────────────────────────────────────────
@admin.register(WeighingTransaction)
class WeighingTransactionAdmin(admin.ModelAdmin):
    list_display  = ('receipt_number', 'farmer', 'vehicle',
                     'gross_weight_kg', 'tare_weight_kg',
                     'net_weight_kg', 'status', 'gross_time')
    list_filter   = ('status',)
    search_fields = ('receipt_number', 'farmer__full_name')
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