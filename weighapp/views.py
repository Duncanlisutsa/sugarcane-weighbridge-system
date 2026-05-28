from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, Farmer, Vehicle, WeighingTransaction, AuditLog


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
    return redirect('login')


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

from django.utils import timezone
from .forms import GrossWeightForm, TareWeightForm, FarmerForm, VehicleForm


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
            transaction = WeighingTransaction.objects.create(
                farmer          = form.cleaned_data['farmer'],
                vehicle         = form.cleaned_data['vehicle'],
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
            messages.success(
                request,
                f"Gross weight recorded. "
                f"Receipt No: {transaction.receipt_number}. "
                f"Now enter the tare weight after offloading."
            )
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

            AuditLog.objects.create(
                user       = request.user,
                action     = 'weight_entry',
                table_name = 'weighingtransaction',
                record_id  = transaction.id,
                new_value  = f"Tare: {transaction.tare_weight_kg}kg | "
                             f"Net: {transaction.net_weight_kg}kg",
                ip_address = get_client_ip(request)
            )
            messages.success(
                request,
                f"Transaction complete! "
                f"Net weight: {transaction.net_weight_kg} kg"
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
    transaction = WeighingTransaction.objects.get(pk=pk)
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