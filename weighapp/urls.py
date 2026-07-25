from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('',        views.login_view,       name='login'),
    path('logout/', views.logout_view,      name='logout'),

    # Dashboards
    path('clerk/',   views.clerk_dashboard,   name='clerk_dashboard'),
    path('manager/', views.manager_dashboard, name='manager_dashboard'),

    # Weighing process
    path('weigh/',          views.weighing_step1, name='weighing_step1'),
    path('weigh/<int:pk>/2/', views.weighing_step2, name='weighing_step2'),
    path('receipt/<int:pk>/', views.receipt,        name='receipt'),

    # Registration
    path('farmer/register/',  views.register_farmer,  name='register_farmer'),
    path('farmer/<int:pk>/edit/', views.edit_farmer,  name='edit_farmer'),
    path('vehicle/register/', views.register_vehicle, name='register_vehicle'),
    path('driver/register/',  views.register_driver,  name='register_driver'),
    path('driver/<int:pk>/edit/', views.edit_driver,  name='edit_driver'),

    # Driver earnings
    path('drivers/',  views.view_drivers,    name='view_drivers'),
    path('earnings/', views.driver_earnings, name='driver_earnings'),
    path('earnings/<int:pk>/toggle-payment/', views.toggle_payment, name='toggle_payment'),

    # Tractor allocation
    path('allocate/',    views.allocate_tractor, name='allocate_tractor'),
    path('allocations/', views.view_allocations, name='view_allocations'),
    path('api/farmer-vehicle/<int:farmer_id>/', views.api_farmer_vehicle, name='api_farmer_vehicle'),
    
    #Reports
    path('reports/', views.reports, name='reports'),
    path('reports/export/', views.export_report_pdf, name='export_report_pdf'),
    
    # User management
    path('users/',            views.manage_users, name='manage_users'),
    path('users/add/',        views.add_user,     name='add_user'),
    path('users/<int:pk>/toggle/', views.toggle_user, name='toggle_user'),
    
    path('users/<int:pk>/reset-password/', views.reset_password, name='reset_password'),
    
    # Manager read-only views
    path('farmers/',  views.view_farmers,  name='view_farmers'),
    path('vehicles/', views.view_vehicles, name='view_vehicles'),
    path('clerks/',   views.view_clerks,   name='view_clerks'),

    # Generic list PDF export (farmers / vehicles / drivers / clerks / earnings)
    path('export/<str:list_type>/', views.export_list_pdf, name='export_list_pdf'),
    ]