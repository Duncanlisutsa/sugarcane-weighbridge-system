from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from .sms import send_gross_weight_sms_async, send_completion_sms_async, send_allocation_sms_async
from .email_utils import send_gross_weight_email_async, send_completion_email_async, send_allocation_email_async
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, Farmer, Vehicle, Driver, WeighingTransaction, AuditLog, TractorAllocation
from .password_utils import validate_password_strength

# ─────────────────────────────────────────
# LANDING PAGE
# ─────────────────────────────────────────
def landing_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    return render(request, 'weighapp/landing.html')
# ─────────────────────────────────────────
# LOGIN VIEW
# ─────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Log the action
            AuditLog.objects.create(
                user=user,
                action='login',
                table_name='user',
                record_id=user.id,
                ip_address=get_client_ip(request)
            )
            return redirect_by_role(user)
        else:
            error = "Invalid username or password. Please try again."

    return render(request, 'weighapp/login.html', {'error': error})


# ─────────────────────────────────────────
# LOGOUT VIEW
# ─────────────────────────────────────────
def logout_view(request):
    if request.user.is_authenticated:
        AuditLog.objects.create(
            user=request.user,
            action='logout',
            table_name='user',
            record_id=request.user.id,
            ip_address=get_client_ip(request)
        )
    logout(request)
    return redirect('landing')


# ─────────────────────────────────────────
# CLERK DASHBOARD
# ─────────────────────────────────────────
@login_required(login_url='login')
def clerk_dashboard(request):
    if request.user.role not in ['clerk', 'admin']:
        return redirect('manager_dashboard')

    from django.utils import timezone
    today = timezone.now().date()

    today_transactions = WeighingTransaction.objects.filter(
        clerk=request.user,
        gross_time__date=today
    ).order_by('-gross_time')

    context = {
        'today_transactions': today_transactions,
        'today_count': today_transactions.count(),
        'today_weight': sum(
            t.net_weight_kg for t in today_transactions
            if t.net_weight_kg
        ),
    }
    return render(request, 'weighapp/clerk_dashboard.html', context)


# ─────────────────────────────────────────
# MANAGER DASHBOARD
# ─────────────────────────────────────────
@login_required(login_url='login')
def manager_dashboard(request):
    if request.user.role not in ['manager', 'admin']:
        return redirect('clerk_dashboard')

    from django.utils import timezone
    today = timezone.now().date()

    all_today = WeighingTransaction.objects.filter(
        gross_time__date=today
    )

    context = {
        'today_count':  all_today.count(),
        'today_weight': sum(
            t.net_weight_kg for t in all_today
            if t.net_weight_kg
        ),
        'total_farmers': Farmer.objects.count(),
        'recent_transactions': WeighingTransaction.objects.order_by(
            '-gross_time'
        )[:10],
    }
    return render(request, 'weighapp/manager_dashboard.html', context)


# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────
def redirect_by_role(user):
    if user.role in ['manager', 'admin']:
        return redirect('manager_dashboard')
    return redirect('clerk_dashboard')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


# ─────────────────────────────────────────
# MANDATORY PASSWORD RESET
# Shown to any user whose account has must_reset_password=True —
# newly created accounts, and accounts an admin has just reset.
# ForcePasswordResetMiddleware redirects here automatically until
# the user completes it.
# ─────────────────────────────────────────
@login_required(login_url='login')
def force_password_reset(request):
    # If the flag is already clear (e.g. they refreshed after
    # succeeding, or reached this URL directly with nothing to do),
    # just send them on to their normal dashboard.
    if not request.user.must_reset_password:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password     = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        password_errors = validate_password_strength(new_password)

        if not request.user.check_password(current_password):
            messages.error(request, "Your current password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        elif password_errors:
            messages.error(
                request,
                "New password must contain " + ", ".join(password_errors) + "."
            )
        elif request.user.check_password(new_password):
            messages.error(
                request,
                "New password must be different from your current password."
            )
        else:
            from django.contrib.auth import update_session_auth_hash

            request.user.set_password(new_password)
            request.user.must_reset_password = False
            request.user.save()
            # Keep the user logged in after changing their own password —
            # otherwise Django invalidates the session on password change.
            update_session_auth_hash(request, request.user)

            AuditLog.objects.create(
                user       = request.user,
                action     = 'password_self_reset',
                table_name = 'user',
                record_id  = request.user.id,
                new_value  = "User completed mandatory password reset",
                ip_address = get_client_ip(request)
            )
            messages.success(request, "Password updated successfully.")
            return redirect_by_role(request.user)

    return render(request, 'weighapp/force_password_reset.html')

from django.utils import timezone
from .forms import GrossWeightForm, TareWeightForm, FarmerForm, VehicleForm, AllocationForm, DriverForm


# ─────────────────────────────────────────
# STEP 1 — Enter gross weight
# ─────────────────────────────────────────
@login_required(login_url='login')
def weighing_step1(request):
    if request.user.role not in ['clerk', 'admin']:
        return redirect('manager_dashboard')

    form = GrossWeightForm()

    if request.method == 'POST':
        form = GrossWeightForm(request.POST)
        if form.is_valid():
            farmer  = form.cleaned_data['farmer']
            vehicle = form.cleaned_data['vehicle']

            # Pull the driver from the active allocation tying this
            # farmer + vehicle together, so earnings can be attributed
            active_allocation = TractorAllocation.objects.filter(
                farmer=farmer,
                vehicle=vehicle,
                status='active'
            ).first()
            driver = active_allocation.driver if active_allocation else None

            transaction = WeighingTransaction.objects.create(
                farmer          = farmer,
                vehicle         = vehicle,
                driver          = driver,
                gross_weight_kg = form.cleaned_data['gross_weight_kg'],
                clerk           = request.user,
                notes           = form.cleaned_data['notes'],
                gross_time      = timezone.now(),
                status          = 'pending',
            )
            AuditLog.objects.create(
                user       = request.user,
                action     = 'weight_entry',
                table_name = 'weighingtransaction',
                record_id  = transaction.id,
                new_value  = f"Gross: {transaction.gross_weight_kg}kg",
                ip_address = get_client_ip(request)
            )
            # Send SMS to farmer in the background — network calls can
            # be slow, so we don't block the redirect on it
            send_gross_weight_sms_async(transaction)
            # Send email to farmer in the background (only if they have
            # one on file) — SMTP can be slow too
            if transaction.farmer.email:
                send_gross_weight_email_async(transaction)

            notice_parts = [
                f"Gross weight recorded.",
                f"Receipt No: {transaction.receipt_number}.",
                f"SMS notification queued for {transaction.farmer.phone}.",
            ]
            if transaction.farmer.email:
                notice_parts.append(f"Email notification queued for {transaction.farmer.email}.")
            notice_parts.append("Now enter the tare weight after offloading.")

            messages.success(request, " ".join(notice_parts))
            return redirect('weighing_step2', pk=transaction.pk)

    return render(request, 'weighapp/weighing_step1.html', {'form': form})


# ─────────────────────────────────────────
# STEP 2 — Enter tare weight
# ─────────────────────────────────────────
@login_required(login_url='login')
def weighing_step2(request, pk):
    if request.user.role not in ['clerk', 'admin']:
        return redirect('manager_dashboard')

    transaction = WeighingTransaction.objects.get(pk=pk)

    form = TareWeightForm(gross_weight=transaction.gross_weight_kg)

    if request.method == 'POST':
        form = TareWeightForm(
            gross_weight=transaction.gross_weight_kg,
            data=request.POST
        )
        if form.is_valid():
            transaction.tare_weight_kg = form.cleaned_data['tare_weight_kg']
            transaction.tare_time      = timezone.now()
            transaction.save()

            # Weighing is complete — free up the vehicle for reallocation
            TractorAllocation.objects.filter(
                vehicle=transaction.vehicle,
                farmer=transaction.farmer,
                status='active'
            ).update(status='completed', released_at=timezone.now())

            AuditLog.objects.create(
                user       = request.user,
                action     = 'weight_entry',
                table_name = 'weighingtransaction',
                record_id  = transaction.id,
                new_value  = f"Tare: {transaction.tare_weight_kg}kg | "
                             f"Net: {transaction.net_weight_kg}kg",
                ip_address = get_client_ip(request)
            )
            # Send completion SMS to farmer in the background
            send_completion_sms_async(transaction)
            # Send completion email to farmer in the background
            # (only if they have one on file)
            if transaction.farmer.email:
                send_completion_email_async(transaction)

            messages.success(
                request,
                f"Transaction complete! "
                f"Net weight: {transaction.net_weight_kg} kg. "
                f"SMS sent to farmer."
            )
            return redirect('receipt', pk=transaction.pk)

    context = {
        'form':        form,
        'transaction': transaction,
    }
    return render(request, 'weighapp/weighing_step2.html', context)


# ─────────────────────────────────────────
# RECEIPT VIEW
# ─────────────────────────────────────────
@login_required(login_url='login')
def receipt(request, pk):
    transaction = WeighingTransaction.objects.prefetch_related('notification_logs').get(pk=pk)
    AuditLog.objects.create(
        user       = request.user,
        action     = 'receipt_printed',
        table_name = 'weighingtransaction',
        record_id  = transaction.id,
        ip_address = get_client_ip(request)
    )
    return render(request, 'weighapp/receipt.html', {
        'transaction': transaction
    })


# ─────────────────────────────────────────
# FARMER REGISTRATION
# ─────────────────────────────────────────
@login_required(login_url='login')
def register_farmer(request):
    if request.user.role not in ['clerk', 'admin']:
        return redirect('manager_dashboard')

    form = FarmerForm()
    if request.method == 'POST':
        form = FarmerForm(request.POST)
        if form.is_valid():
            farmer = form.save(commit=False)
            farmer.registered_by = request.user
            farmer.save()
            AuditLog.objects.create(
                user       = request.user,
                action     = 'farmer_created',
                table_name = 'farmer',
                record_id  = farmer.id,
                new_value  = farmer.full_name,
                ip_address = get_client_ip(request)
            )
            messages.success(
                request,
                f"Farmer {farmer.full_name} registered successfully."
            )
            return redirect('clerk_dashboard')

    return render(request, 'weighapp/register_farmer.html', {'form': form})


# ─────────────────────────────────────────
# FARMER EDIT (admin + clerk)
# ─────────────────────────────────────────
@login_required(login_url='login')
def edit_farmer(request, pk):
    if request.user.role not in ['clerk', 'admin']:
        return redirect('manager_dashboard')

    try:
        farmer = Farmer.objects.get(pk=pk)
    except Farmer.DoesNotExist:
        messages.error(request, "Farmer not found.")
        return redirect('view_farmers')

    if request.method == 'POST':
        form = FarmerForm(request.POST, instance=farmer)
        if form.is_valid():
            old_name = farmer.full_name
            form.save()
            AuditLog.objects.create(
                user       = request.user,
                action     = 'farmer_updated',
                table_name = 'farmer',
                record_id  = farmer.id,
                old_value  = old_name,
                new_value  = farmer.full_name,
                ip_address = get_client_ip(request)
            )
            messages.success(
                request,
                f"Farmer {farmer.full_name} updated successfully."
            )
            return redirect('view_farmers')
    else:
        form = FarmerForm(instance=farmer)

    return render(request, 'weighapp/edit_farmer.html', {
        'form': form,
        'farmer': farmer,
    })


# ─────────────────────────────────────────
# VEHICLE REGISTRATION
# ─────────────────────────────────────────
@login_required(login_url='login')
def register_vehicle(request):
    if request.user.role not in ['clerk', 'admin']:
        return redirect('manager_dashboard')

    form = VehicleForm()
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.registered_by = request.user
            vehicle.save()
            AuditLog.objects.create(
                user       = request.user,
                action     = 'vehicle_created',
                table_name = 'vehicle',
                record_id  = vehicle.id,
                new_value  = vehicle.plate_number,
                ip_address = get_client_ip(request)
            )
            messages.success(
                request,
                f"Vehicle {vehicle.plate_number} registered successfully."
            )
            return redirect('clerk_dashboard')

    return render(request, 'weighapp/register_vehicle.html', {'form': form})


# ─────────────────────────────────────────
# DRIVER REGISTRATION
# ─────────────────────────────────────────
@login_required(login_url='login')
def register_driver(request):
    if request.user.role not in ['clerk', 'admin']:
        return redirect('manager_dashboard')

    form = DriverForm()
    if request.method == 'POST':
        form = DriverForm(request.POST)
        if form.is_valid():
            driver = form.save(commit=False)
            driver.registered_by = request.user
            driver.save()
            AuditLog.objects.create(
                user       = request.user,
                action     = 'driver_created',
                table_name = 'driver',
                record_id  = driver.id,
                new_value  = driver.full_name,
                ip_address = get_client_ip(request)
            )
            messages.success(
                request,
                f"Driver {driver.full_name} ({driver.driver_code}) registered successfully."
            )
            return redirect('clerk_dashboard')

    return render(request, 'weighapp/register_driver.html', {'form': form})


# ─────────────────────────────────────────
# DRIVER EDIT (admin + clerk)
# ─────────────────────────────────────────
@login_required(login_url='login')
def edit_driver(request, pk):
    if request.user.role not in ['clerk', 'admin']:
        return redirect('manager_dashboard')

    try:
        driver = Driver.objects.get(pk=pk)
    except Driver.DoesNotExist:
        messages.error(request, "Driver not found.")
        return redirect('view_drivers')

    if request.method == 'POST':
        form = DriverForm(request.POST, instance=driver)
        if form.is_valid():
            old_name = driver.full_name
            form.save()
            AuditLog.objects.create(
                user       = request.user,
                action     = 'driver_updated',
                table_name = 'driver',
                record_id  = driver.id,
                old_value  = old_name,
                new_value  = driver.full_name,
                ip_address = get_client_ip(request)
            )
            messages.success(
                request,
                f"Driver {driver.full_name} updated successfully."
            )
            return redirect('view_drivers')
    else:
        form = DriverForm(instance=driver)

    return render(request, 'weighapp/edit_driver.html', {
        'form': form,
        'driver': driver,
    })


# ─────────────────────────────────────────
# VIEW DRIVERS (admin, manager, clerk)
# ─────────────────────────────────────────
@login_required(login_url='login')
def view_drivers(request):
    if request.user.role not in ['manager', 'admin', 'clerk']:
        return redirect('clerk_dashboard')

    drivers = Driver.objects.all().order_by('full_name')
    context = {
        'drivers': drivers,
        'total':   drivers.count(),
    }
    return render(request, 'weighapp/view_drivers.html', context)


# ─────────────────────────────────────────
# DRIVER EARNINGS (admin, manager, clerk can view;
# only admin/manager can mark payments)
# ─────────────────────────────────────────
@login_required(login_url='login')
def driver_earnings(request):
    if request.user.role not in ['manager', 'admin', 'clerk']:
        return redirect('clerk_dashboard')

    from django.db.models import Sum, Count, Q

    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    driver_id = request.GET.get('driver', '')

    transactions = WeighingTransaction.objects.filter(
        status='complete',
        driver__isnull=False
    ).select_related('driver', 'farmer', 'vehicle').order_by('-gross_time')

    if date_from:
        transactions = transactions.filter(gross_time__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(gross_time__date__lte=date_to)
    if driver_id:
        transactions = transactions.filter(driver__id=driver_id)

    # Per-driver summary: total tonnage, total earnings, unpaid count
    drivers_summary = []
    for driver in Driver.objects.all().order_by('full_name'):
        driver_txns = transactions.filter(driver=driver)
        if not driver_txns.exists():
            continue
        total_net_kg = driver_txns.aggregate(t=Sum('net_weight_kg'))['t'] or 0
        total_tons = total_net_kg / 1000
        total_earnings = round(total_tons * settings.RATE_PER_TON_KES, 2)
        unpaid_count = driver_txns.filter(payment_status='unpaid').count()
        unpaid_earnings = round(
            (driver_txns.filter(payment_status='unpaid').aggregate(
                t=Sum('net_weight_kg'))['t'] or 0) / 1000 * settings.RATE_PER_TON_KES, 2
        )
        drivers_summary.append({
            'driver':          driver,
            'trip_count':      driver_txns.count(),
            'total_tons':      round(total_tons, 2),
            'total_earnings':  total_earnings,
            'unpaid_count':    unpaid_count,
            'unpaid_earnings': unpaid_earnings,
        })

    drivers_for_filter = Driver.objects.all().order_by('full_name')

    context = {
        'transactions':       transactions,
        'drivers_summary':    drivers_summary,
        'drivers_for_filter': drivers_for_filter,
        'date_from':          date_from,
        'date_to':            date_to,
        'driver_id':          driver_id,
        'rate_per_ton':       settings.RATE_PER_TON_KES,
    }
    return render(request, 'weighapp/driver_earnings.html', context)


# ─────────────────────────────────────────
# TOGGLE A SINGLE TRANSACTION'S PAYMENT STATUS
# Restricted to admin/manager — this is a financial action,
# separate from the read-only earnings view clerks can see.
# ─────────────────────────────────────────
@login_required(login_url='login')
def toggle_payment(request, pk):
    if request.user.role not in ['manager', 'admin']:
        return redirect('clerk_dashboard')

    try:
        transaction = WeighingTransaction.objects.get(pk=pk)
    except WeighingTransaction.DoesNotExist:
        messages.error(request, "Transaction not found.")
        return redirect('driver_earnings')

    if request.method == 'POST':
        if transaction.payment_status == 'unpaid':
            transaction.payment_status = 'paid'
            transaction.paid_at = timezone.now()
            transaction.paid_by = request.user
        else:
            transaction.payment_status = 'unpaid'
            transaction.paid_at = None
            transaction.paid_by = None
        transaction.save()

        AuditLog.objects.create(
            user       = request.user,
            action     = 'payment_marked',
            table_name = 'weighingtransaction',
            record_id  = transaction.id,
            new_value  = f"Payment status: {transaction.payment_status}",
            ip_address = get_client_ip(request)
        )
        messages.success(
            request,
            f"{transaction.receipt_number} marked as {transaction.payment_status}."
        )

    return redirect('driver_earnings')


# ─────────────────────────────────────────
# ALLOCATE TRACTOR TO FARMER
# ─────────────────────────────────────────
@login_required(login_url='login')
def allocate_tractor(request):
    if request.user.role not in ['clerk', 'admin']:
        return redirect('manager_dashboard')

    form = AllocationForm()
    if request.method == 'POST':
        form = AllocationForm(request.POST)
        if form.is_valid():
            vehicle = form.cleaned_data['vehicle']
            farmer  = form.cleaned_data['farmer']
            driver  = form.cleaned_data['driver']

            # Guard against a stale dropdown / race condition where the
            # vehicle or driver got allocated between page load and submit
            if TractorAllocation.objects.filter(vehicle=vehicle, status='active').exists():
                messages.error(
                    request,
                    f"{vehicle.plate_number} is already allocated to a farmer."
                )
            elif TractorAllocation.objects.filter(driver=driver, status='active').exists():
                messages.error(
                    request,
                    f"{driver.full_name} is already allocated to another tractor."
                )
            else:
                allocation = TractorAllocation.objects.create(
                    vehicle      = vehicle,
                    farmer       = farmer,
                    driver       = driver,
                    allocated_by = request.user,
                )

                # Notify the farmer that a vehicle/driver has been
                # allocated to collect their delivery — in the
                # background, same pattern as the weighing notifications
                send_allocation_sms_async(allocation)
                if farmer.email:
                    send_allocation_email_async(allocation)

                notice_parts = [
                    f"{vehicle.plate_number} allocated to {farmer.full_name}, driven by {driver.full_name}.",
                    f"SMS notification queued for {farmer.phone}.",
                ]
                if farmer.email:
                    notice_parts.append(f"Email notification queued for {farmer.email}.")

                messages.success(request, " ".join(notice_parts))
                return redirect('view_allocations')

    return render(request, 'weighapp/allocate_tractor.html', {'form': form})


# ─────────────────────────────────────────
# TRACTOR ALLOCATION STATUS BOARD
# ─────────────────────────────────────────
@login_required(login_url='login')
def view_allocations(request):
    active_allocations = TractorAllocation.objects.filter(
        status='active'
    ).select_related('vehicle', 'farmer', 'driver').prefetch_related('notification_logs').order_by('allocated_at')

    completed_allocations = TractorAllocation.objects.filter(
        status='completed'
    ).select_related('vehicle', 'farmer', 'driver').prefetch_related('notification_logs').order_by('-released_at')[:20]

    context = {
        'active_allocations':    active_allocations,
        'completed_allocations': completed_allocations,
    }
    return render(request, 'weighapp/view_allocations.html', context)


# ─────────────────────────────────────────
# API: get a farmer's currently allocated vehicle
# (used by weighing_step1 to filter the vehicle dropdown)
# ─────────────────────────────────────────
@login_required(login_url='login')
def api_farmer_vehicle(request, farmer_id):
    allocation = TractorAllocation.objects.filter(
        farmer_id=farmer_id,
        status='active'
    ).select_related('vehicle').first()

    if allocation:
        return JsonResponse({
            'has_vehicle':   True,
            'vehicle_id':    allocation.vehicle.id,
            'vehicle_label': f"{allocation.vehicle.plate_number} - {allocation.vehicle.make_model}",
        })

    return JsonResponse({'has_vehicle': False})


# ─────────────────────────────────────────
# REPORTS VIEW
# ─────────────────────────────────────────
@login_required(login_url='login')
def reports(request):
    if request.user.role not in ['manager', 'admin']:
        return redirect('clerk_dashboard')

    from django.db.models import Sum, Count

    # Get filter values from the request
    date_from   = request.GET.get('date_from', '')
    date_to     = request.GET.get('date_to', '')
    farmer_id   = request.GET.get('farmer', '')

    # Start with all complete transactions
    transactions = WeighingTransaction.objects.filter(
        status='complete'
    ).order_by('-gross_time')

    # Apply filters
    if date_from:
        transactions = transactions.filter(
            gross_time__date__gte=date_from
        )
    if date_to:
        transactions = transactions.filter(
            gross_time__date__lte=date_to
        )
    if farmer_id:
        transactions = transactions.filter(
            farmer__id=farmer_id
        )

    # Calculate totals
    totals = transactions.aggregate(
        total_weight = Sum('net_weight_kg'),
        total_count  = Count('id')
    )

    # Get all farmers for the filter dropdown
    farmers = Farmer.objects.all()

    # Log the report view
    AuditLog.objects.create(
        user       = request.user,
        action     = 'report_viewed',
        table_name = 'weighingtransaction',
        ip_address = get_client_ip(request)
    )

    context = {
        'transactions': transactions,
        'farmers':      farmers,
        'totals':       totals,
        'date_from':    date_from,
        'date_to':      date_to,
        'farmer_id':    farmer_id,
    }
    return render(request, 'weighapp/reports.html', context)


# ─────────────────────────────────────────
# EXPORT REPORT TO PDF
# ─────────────────────────────────────────
@login_required(login_url='login')
def export_report_pdf(request):
    if request.user.role not in ['manager', 'admin']:
        return redirect('clerk_dashboard')

    from django.db.models import Sum, Count
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer
    )
    from reportlab.lib.styles import getSampleStyleSheet
    import datetime

    # Apply same filters
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    farmer_id = request.GET.get('farmer', '')

    transactions = WeighingTransaction.objects.filter(
        status='complete'
    ).order_by('-gross_time')

    if date_from:
        transactions = transactions.filter(
            gross_time__date__gte=date_from
        )
    if date_to:
        transactions = transactions.filter(
            gross_time__date__lte=date_to
        )
    if farmer_id:
        transactions = transactions.filter(farmer__id=farmer_id)

    totals = transactions.aggregate(
        total_weight=Sum('net_weight_kg'),
        total_count=Count('id')
    )

    # Build PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        'attachment; filename="weighbridge_report.pdf"'
    )

    doc    = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    story  = []

    # Title
    story.append(Paragraph(
        "Sugarcane Weighbridge System — Report",
        styles['Title']
    ))
    story.append(Paragraph(
        f"Generated: {datetime.datetime.now().strftime('%d %B %Y %H:%M')}",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.4 * cm))

    # Summary
    story.append(Paragraph(
        f"Total Transactions: {totals['total_count']}  |  "
        f"Total Net Weight: {totals['total_weight'] or 0} kg",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.4 * cm))

    # Table header
    data = [[
        'Receipt No.', 'Farmer', 'Vehicle',
        'Gross (kg)', 'Tare (kg)', 'Net (kg)', 'Date'
    ]]

    # Table rows
    for t in transactions:
        data.append([
            t.receipt_number,
            t.farmer.full_name,
            t.vehicle.plate_number,
            str(t.gross_weight_kg),
            str(t.tare_weight_kg),
            str(t.net_weight_kg),
            t.gross_time.strftime('%d/%m/%Y %H:%M'),
        ])

    # Style the table
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B5E20')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 9),
        ('FONTSIZE',   (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#F1F8E9')]),
        ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN',      (0, 0), (-1, -1), 'LEFT'),
        ('PADDING',    (0, 0), (-1, -1), 4),
    ]))

    story.append(table)
    doc.build(story)
    return response


# ─────────────────────────────────────────
# USER MANAGEMENT — Admin only
# ─────────────────────────────────────────
@login_required(login_url='login')
def manage_users(request):
    if request.user.role != 'admin':
        return redirect('clerk_dashboard')

    users = User.objects.filter(is_superuser=False).order_by('role', 'full_name')
    return render(request, 'weighapp/manage_users.html', {'users': users})


@login_required(login_url='login')
def add_user(request):
    if request.user.role != 'admin':
        return redirect('clerk_dashboard')

    if request.method == 'POST':
        username  = request.POST.get('username')
        full_name = request.POST.get('full_name')
        email     = request.POST.get('email')
        role      = request.POST.get('role')
        password  = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
            return redirect('add_user')

        password_errors = validate_password_strength(password)
        if password_errors:
            messages.error(
                request,
                "Password must contain " + ", ".join(password_errors) + "."
            )
            return redirect('add_user')

        user = User.objects.create_user(
            username  = username,
            password  = password,
            email     = email,
            full_name = full_name,
            role      = role,
            must_reset_password = True,
        )
        AuditLog.objects.create(
            user       = request.user,
            action     = 'user_created',
            table_name = 'user',
            record_id  = user.id,
            new_value  = f"{full_name} ({role})",
            ip_address = get_client_ip(request)
        )
        messages.success(
            request,
            f"User {full_name} created successfully. They will be asked "
            f"to set their own password the first time they log in."
        )
        return redirect('manage_users')

    return render(request, 'weighapp/add_user.html', {})


@login_required(login_url='login')
def toggle_user(request, pk):
    if request.user.role != 'admin':
        return redirect('clerk_dashboard')

    user = User.objects.get(pk=pk)
    user.is_active = not user.is_active
    user.save()
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User {user.full_name} {status}.")
    return redirect('manage_users')

# ─────────────────────────────────────────
# RESET USER PASSWORD — Admin only
# ─────────────────────────────────────────
@login_required(login_url='login')
def reset_password(request, pk):
    if request.user.role != 'admin':
        return redirect('clerk_dashboard')

    user = User.objects.get(pk=pk)

    if request.method == 'POST':
        new_password  = request.POST.get('new_password')
        confirm       = request.POST.get('confirm_password')

        if new_password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('reset_password', pk=pk)

        password_errors = validate_password_strength(new_password)
        if password_errors:
            messages.error(
                request,
                "Password must contain " + ", ".join(password_errors) + "."
            )
            return redirect('reset_password', pk=pk)

        user.set_password(new_password)
        user.must_reset_password = True
        user.save()

        AuditLog.objects.create(
            user       = request.user,
            action     = 'password_reset_by_admin',
            table_name = 'user',
            record_id  = user.id,
            new_value  = f"Password reset for {user.full_name}",
            ip_address = get_client_ip(request)
        )

        messages.success(
            request,
            f"Password for {user.full_name} has been reset successfully. "
            f"They will be asked to set their own password next time they log in."
        )
        return redirect('manage_users')

    return render(request, 'weighapp/reset_password.html', {'target_user': user})

# ─────────────────────────────────────────
# MANAGER — VIEW FARMERS
# ─────────────────────────────────────────
@login_required(login_url='login')
def view_farmers(request):
    if request.user.role not in ['manager', 'admin', 'clerk']:
        return redirect('clerk_dashboard')

    farmers = Farmer.objects.all().order_by('zone', 'full_name')
    context = {
        'farmers': farmers,
        'total': farmers.count(),
    }
    return render(request, 'weighapp/view_farmers.html', context)


# ─────────────────────────────────────────
# MANAGER — VIEW VEHICLES
# ─────────────────────────────────────────
@login_required(login_url='login')
def view_vehicles(request):
    if request.user.role not in ['manager', 'admin']:
        return redirect('clerk_dashboard')

    vehicles = Vehicle.objects.all().order_by('plate_number')

    active_allocations = {
        a.vehicle_id: a
        for a in TractorAllocation.objects.filter(status='active').select_related('farmer')
    }
    for v in vehicles:
        v.current_allocation = active_allocations.get(v.id)

    context = {
        'vehicles': vehicles,
        'total': vehicles.count(),
    }
    return render(request, 'weighapp/view_vehicles.html', context)


# ─────────────────────────────────────────
# MANAGER — VIEW CLERKS
# ─────────────────────────────────────────
@login_required(login_url='login')
def view_clerks(request):
    if request.user.role not in ['manager', 'admin']:
        return redirect('clerk_dashboard')

    clerks = User.objects.filter(
        role='clerk',
        is_superuser=False
    ).order_by('full_name')
    context = {
        'clerks': clerks,
        'total': clerks.count(),
    }
    return render(request, 'weighapp/view_clerks.html', context)

    # ─────────────────────────────────────────
# GENERIC PDF EXPORT — Farmers, Vehicles,
# Drivers, Clerks, Driver Earnings summary
# ─────────────────────────────────────────
@login_required(login_url='login')
def export_list_pdf(request, list_type):
    from django.db.models import Sum
    from django.http import HttpResponse, Http404
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer
    )
    from reportlab.lib.styles import getSampleStyleSheet
    import datetime

    allowed_roles = {
        'farmers':  ['manager', 'admin', 'clerk'],
        'vehicles': ['manager', 'admin'],
        'drivers':  ['manager', 'admin', 'clerk'],
        'clerks':   ['manager', 'admin'],
        'earnings': ['manager', 'admin', 'clerk'],
    }
    if list_type not in allowed_roles:
        raise Http404("Unknown report type.")
    if request.user.role not in allowed_roles[list_type]:
        return redirect('clerk_dashboard')

    titles = {
        'farmers':  'Registered Farmers',
        'vehicles': 'Registered Vehicles',
        'drivers':  'Registered Drivers',
        'clerks':   'System Clerks',
        'earnings': 'Driver Earnings Summary',
    }

    # Build the header row + data rows per list type
    if list_type == 'farmers':
        header = ['#', 'Farmer Code', 'Full Name', 'ID Number', 'Phone', 'Zone', 'Date Registered']
        rows = Farmer.objects.all().order_by('zone', 'full_name')
        data = [[
            i + 1, f.farmer_code, f.full_name, f.id_number, f.phone,
            f.zone, f.created_at.strftime('%d/%m/%Y')
        ] for i, f in enumerate(rows)]

    elif list_type == 'vehicles':
        header = ['#', 'Plate Number', 'Make & Model', 'Status', 'Date Registered']
        rows = Vehicle.objects.all().order_by('plate_number')
        active_allocations = {
            a.vehicle_id: a
            for a in TractorAllocation.objects.filter(status='active')
        }
        data = []
        for i, v in enumerate(rows):
            status = 'Allocated' if active_allocations.get(v.id) else 'Available'
            data.append([i + 1, v.plate_number, v.make_model, status, v.created_at.strftime('%d/%m/%Y')])

    elif list_type == 'drivers':
        header = ['#', 'Driver Code', 'Full Name', 'Phone', 'ID Number', 'Date Registered']
        rows = Driver.objects.all().order_by('full_name')
        data = [[
            i + 1, d.driver_code, d.full_name, d.phone, d.id_number,
            d.created_at.strftime('%d/%m/%Y')
        ] for i, d in enumerate(rows)]

    elif list_type == 'clerks':
        header = ['#', 'Full Name', 'Username', 'Email', 'Status', 'Date Added']
        rows = User.objects.filter(role='clerk', is_superuser=False).order_by('full_name')
        data = [[
            i + 1, c.full_name, c.username, c.email or '—',
            'Active' if c.is_active else 'Inactive', c.date_joined.strftime('%d/%m/%Y')
        ] for i, c in enumerate(rows)]

    elif list_type == 'earnings':
        date_from = request.GET.get('date_from', '')
        date_to   = request.GET.get('date_to', '')
        driver_id = request.GET.get('driver', '')

        transactions = WeighingTransaction.objects.filter(
            status='complete', driver__isnull=False
        )
        if date_from:
            transactions = transactions.filter(gross_time__date__gte=date_from)
        if date_to:
            transactions = transactions.filter(gross_time__date__lte=date_to)
        if driver_id:
            transactions = transactions.filter(driver__id=driver_id)

        header = ['Driver', 'Trips', 'Total Tons', 'Total Earnings (Ksh.)', 'Unpaid Trips', 'Unpaid Amount (Ksh.)']
        data = []
        for driver in Driver.objects.all().order_by('full_name'):
            driver_txns = transactions.filter(driver=driver)
            if not driver_txns.exists():
                continue
            total_net_kg = driver_txns.aggregate(t=Sum('net_weight_kg'))['t'] or 0
            total_tons = total_net_kg / 1000
            total_earnings = round(total_tons * settings.RATE_PER_TON_KES, 2)
            unpaid_count = driver_txns.filter(payment_status='unpaid').count()
            unpaid_earnings = round(
                (driver_txns.filter(payment_status='unpaid').aggregate(
                    t=Sum('net_weight_kg'))['t'] or 0) / 1000 * settings.RATE_PER_TON_KES, 2
            )
            data.append([
                f"{driver.driver_code} — {driver.full_name}", driver_txns.count(),
                round(total_tons, 2), total_earnings, unpaid_count, unpaid_earnings
            ])

    # Build PDF — opens inline in the browser so it can be printed directly
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{list_type}_report.pdf"'

    doc    = SimpleDocTemplate(response, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story  = []

    story.append(Paragraph(f"Sugarcane Weighbridge System — {titles[list_type]}", styles['Title']))
    story.append(Paragraph(
        f"Generated: {datetime.datetime.now().strftime('%d %B %Y %H:%M')}",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(f"Total Records: {len(data)}", styles['Normal']))
    story.append(Spacer(1, 0.4 * cm))

    table = Table([header] + data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B5E20')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 9),
        ('FONTSIZE',   (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F8E9')]),
        ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN',      (0, 0), (-1, -1), 'LEFT'),
        ('PADDING',    (0, 0), (-1, -1), 4),
    ]))

    story.append(table)
    doc.build(story)
    return response


    # ─────────────────────────────────────────
# AUDIT LOG — Admin only, read-only
# Every login, logout, record creation/update, payment change,
# report view and receipt print is written to AuditLog as it
# happens (see the AuditLog.objects.create(...) calls throughout
# this file). This view is just the in-app window onto that trail
# so an admin doesn't need Django admin credentials to check it —
# filterable by user/action/date and paginated since the table
# only grows.
# ─────────────────────────────────────────
@login_required(login_url='login')
def view_audit_log(request):
    if request.user.role != 'admin':
        return redirect('clerk_dashboard')

    from django.core.paginator import Paginator

    logs = AuditLog.objects.select_related('user').all()

    user_id   = request.GET.get('user', '')
    action    = request.GET.get('action', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    if user_id:
        logs = logs.filter(user__id=user_id)
    if action:
        logs = logs.filter(action=action)
    if date_from:
        logs = logs.filter(logged_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(logged_at__date__lte=date_to)

    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj':   page_obj,
        'users':      User.objects.filter(is_superuser=False).order_by('full_name'),
        'actions':    AuditLog.ACTION_CHOICES,
        'user_id':    user_id,
        'action':     action,
        'date_from':  date_from,
        'date_to':    date_to,
    }
    return render(request, 'weighapp/audit_log.html', context)