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
    path('vehicle/register/', views.register_vehicle, name='register_vehicle'),
    
    #Reports
    path('reports/', views.reports, name='reports'),
    path('reports/export/', views.export_report_pdf, name='export_report_pdf'),
    
    # User management
    path('users/',            views.manage_users, name='manage_users'),
    path('users/add/',        views.add_user,     name='add_user'),
    path('users/<int:pk>/toggle/', views.toggle_user, name='toggle_user'),
    ]

