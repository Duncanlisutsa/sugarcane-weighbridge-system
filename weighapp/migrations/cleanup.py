"""
One-off cleanup script: removes ONLY the fake data created by the old
seed_data.py script (plus any transactions that reference that seed data),
leaving any other real farmers/vehicles/clerks/transactions untouched.

Run once:
    python cleanup_seed_data.py

Then delete this file.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'weighbridge.settings')
django.setup()

from django.db.models import Q
from weighapp.models import User, Farmer, Vehicle, WeighingTransaction

# --- Identify seed clerks: usernames clerk01 - clerk10 ---
seed_clerk_ids = list(User.objects.filter(
    username__regex=r'^clerk(0[1-9]|10)$',
    role='clerk'
).values_list('id', flat=True))
print(f"Seed clerks found: {len(seed_clerk_ids)}")

# --- Identify seed farmers: 4-digit codes FC0001-FC0100 ---
# (your new auto-generated codes are 3-digit: FC001, FC002, ...)
seed_farmer_ids = list(Farmer.objects.filter(
    farmer_code__regex=r'^FC[0-9]{4}$'
).values_list('id', flat=True))
print(f"Seed farmers found: {len(seed_farmer_ids)}")

# --- Identify seed vehicles: linked to seed farmers or seed clerks ---
seed_vehicle_ids = list(Vehicle.objects.filter(
    Q(farmer_id__in=seed_farmer_ids) | Q(registered_by_id__in=seed_clerk_ids)
).values_list('id', flat=True))
print(f"Seed vehicles found: {len(seed_vehicle_ids)}")

# --- Identify transactions to delete: seed-tagged, OR referencing any
#     seed farmer / seed vehicle / seed clerk (e.g. test weighings done
#     against seed data before real data existed) ---
seed_transaction_ids = list(WeighingTransaction.objects.filter(
    Q(notes='Sample data') |
    Q(farmer_id__in=seed_farmer_ids) |
    Q(vehicle_id__in=seed_vehicle_ids) |
    Q(clerk_id__in=seed_clerk_ids)
).values_list('id', flat=True))
print(f"Transactions to delete found: {len(seed_transaction_ids)}")

# --- Delete in order: transactions -> vehicles -> farmers -> clerks ---
t_count, _ = WeighingTransaction.objects.filter(id__in=seed_transaction_ids).delete()
print(f"Deleted {t_count} transaction-related rows")

v_count, _ = Vehicle.objects.filter(id__in=seed_vehicle_ids).delete()
print(f"Deleted {v_count} vehicle-related rows")

f_count, _ = Farmer.objects.filter(id__in=seed_farmer_ids).delete()
print(f"Deleted {f_count} farmer-related rows")

c_count, _ = User.objects.filter(id__in=seed_clerk_ids).delete()
print(f"Deleted {c_count} clerk-related rows")

print("Cleanup complete.")