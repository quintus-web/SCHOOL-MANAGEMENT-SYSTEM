# finance/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Core Home & Admin Consoles
    path('', views.main_portal_home, name='public_home'),
    path('dev/debug-console/', views.developer_debug_console_hub, name='dev_debug_console'),
    
    # Section A: Student Information Desks
    path('students/registry/', views.student_registry_workstation, name='student_registry'),
    path('students/profile/<int:student_id>/', views.single_student_profile_folder, name='student_profile'),
    
    # Section B: Staff & HR Directories
    path('staff/registry-matrix/', views.staff_management_matrix, name='staff_management_matrix'),
    path('staff/faculty-directory/', views.faculty_directory, name='faculty_directory'),
    
    # Section C: Finance Accounts
    path('finance/dashboard/', views.bursar_dashboard, name='bursar_dashboard'),
    path('finance/statement/<int:student_id>/', views.student_account_statement, name='student_statement'),
    path('finance/collect-fee/<int:student_id>/', views.collect_fee_payment, name='collect_fee_payment'),
    path('finance/defaulters-sms/', views.fee_defaulters_sms_portal, name='fee_defaulters_portal'),
    
    # Section D: Academic & Security Paths
    path('academic/marks-entry/', views.marks_entry_portal, name='marks_entry_portal'),
    path('academic/analytics/', views.academic_analytics_dashboard, name='academic_analytics'),
    path('auth/login/', views.staff_login_view, name='staff_login'),
    path('auth/logout/', views.staff_logout_view, name='staff_logout'),
    path('operations/attendance/', views.global_attendance_control_deck, name='attendance_deck'),

    # Inside finance/urls.py
    # ... your existing routes ...

    # Master Parent Portal Path
    path('parent/portal/', views.parent_portal_gateway, name='parent_portal_gateway'),
    
    # 🛡️ Dynamic Aliases: These resolve the legacy template strings instantly
    path('parent/portal/v1/', views.parent_portal_gateway, name='parent_gateway'),
    path('parent/portal/login/', views.parent_portal_gateway, name='parent_gateway_login'),

    path('operations/inventory/', views.inventory_asset_control_deck, name='inventory_deck'),
]