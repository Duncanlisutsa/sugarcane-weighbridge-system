import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'weighbridge.settings')
django.setup()

import random
from datetime import timedelta
from django.utils import timezone
from weighapp.models import User, Farmer, Vehicle, WeighingTransaction

zones = ['North', 'South', 'East', 'West', 'Central']
clerks = []
for i in range(1, 11):
    u, created = User.objects.get_or_create(username=f'clerk{i:02d}')
    u.full_name = f'Clerk User {i}'
    u.role = 'clerk'
    u.set_password('pass@2026')
    u.save()
    clerks.append(u)
print("10 clerks done")

first_names = ['John','Mary','Peter','Grace','James','Esther','David','Ruth','Paul','Faith','Joseph','Agnes','Daniel','Rose','Samuel','Alice','Michael','Jane','Robert','Ann']
last_names = ['Wanjiru','Otieno','Kamau','Omondi','Mwangi','Achieng','Kimani','Owino','Njoroge','Adhiambo','Mutua','Awuor','Kariuki','Auma','Musyoka','Atieno','Gitau','Nyambura','Waweru','Okello']

farmers = list(Farmer.objects.all())
for i in range(1, 101):
    fn = random.choice(first_names)
    ln = random.choice(last_names)
    farmer, created = Farmer.objects.get_or_create(
        farmer_code=f'FC{i:04d}',
        defaults={
            'full_name': f'{fn} {ln}',
            'id_number': f'{30000000 + i}',
            'phone': f'07{random.randint(10000000,99999999)}',
            'zone': random.choice(zones),
            'registered_by': random.choice(clerks),
        }
    )
    if farmer not in farmers:
        farmers.append(farmer)
print("100 farmers done")

makes = ['Isuzu NPR','Mitsubishi Canter','Toyota Dyna','Tata LPT','Nissan UD']
vehicles = list(Vehicle.objects.all())
for i in range(1, 51):
    plate = f'K{random.choice(["AA","BB","CC","DD","EE"])}{100+i}{"ABCDEFGH"[i%8]}'
    vehicle, created = Vehicle.objects.get_or_create(
        plate_number=plate,
        defaults={
            'make_model': random.choice(makes),
            'farmer': random.choice(farmers),
            'registered_by': random.choice(clerks),
        }
    )
    if vehicle not in vehicles:
        vehicles.append(vehicle)
print("50 vehicles done")

now = timezone.now()
for i in range(150):
    days_ago = random.randint(0, 60)
    gross_time = now - timedelta(days=days_ago, hours=random.randint(6, 17))
    gross = round(random.uniform(8000, 25000), 2)
    tare = round(random.uniform(3000, 6000), 2)
    date_str = gross_time.strftime('%Y%m%d')
    receipt = f"WB-{date_str}-{i+1000:04d}"
    t = WeighingTransaction(
        farmer=random.choice(farmers),
        vehicle=random.choice(vehicles),
        gross_weight_kg=gross,
        tare_weight_kg=tare,
        gross_time=gross_time,
        tare_time=gross_time + timedelta(hours=random.randint(1, 4)),
        clerk=random.choice(clerks),
        status='complete',
        notes='Sample data',
        receipt_number=receipt,
    )
    t.save()
print("150 transactions done")
print("All done!")
