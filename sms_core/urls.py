# sms_core/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('finance.urls')),  # Forces Django to unpack strings, not modules
]
# finance/urls.py
from django.urls import path
from finance import views

urlpatterns = [
    # ── CORE ACCESSIBLE WEB CHANNELS ──
    path('', views.bursar_dashboard, name='public_home'),
    path('dev/debug-console/', views.developer_debug_console_hub, name='dev_debug_console'),
    
    # ── SECURITY & SESSIONS ACCESS WORKSPACES ──
    path('gateway/login/', views.staff_login_view, name='staff_login'),
    path('gateway/logout/', views.staff_logout_view, name='staff_logout'),
    path('portal/executive-kpis/', views.executive_analytics_kpi_dashboard, name='executive_kpis'),
    
    # ── STUDENT OPERATIONAL DIRECTORY ──
    path('registry/learners/', views.student_registry_workstation, name='student_registry'),
    path('registry/learners/<int:student_id>/folder/', views.single_student_profile_folder, name='student_profile'),
    path('registry/staff-matrix/', views.staff_management_matrix, name='staff_management_matrix'),
    path('registry/faculty/', views.faculty_directory, name='faculty_directory'),
    
    # ── BURSAR ACCOUNTING ENGINE & LEDGERS ──
    path('treasury/ledger/', views.bursar_dashboard, name='bursar_dashboard'),
    path('treasury/statement/<int:student_id>/', views.student_account_statement, name='student_statement'),
    path('treasury/collect-fees/<int:student_id>/', views.collect_fee_payment, name='collect_fee_payment'),
    path('treasury/defaulters-sms/', views.fee_defaulters_portal, name='fee_defaulters_portal'),
    
    # ── FACULTY BROADCASTER ENGINE ──
    path('faculty/class-broadcast/', views.teacher_sms_broadcast, name='teacher_sms_broadcast'),

    # ── ACADEMIC EVALUATION WORKSPACE ──
    path('academic/management-hub/', views.academic_management_hub, name='academic_hub'),
    path('academic/grading-desk/', views.marks_entry_portal, name='marks_entry_portal'),
    path('academic/analytics/', views.academic_analytics_dashboard, name='academic_analytics'),
    path('academic/report-card/<int:student_id>/pdf/', views.generate_report_card_view, name='generate_report_card'),
    
    # ── EXTERNAL PARENT GATEWAY SYSTEM ──
    path('parent-portal/', views.parent_portal_gateway, name='parent_portal_gateway'),
    
    # ── ROUTINE ASSET LOGISTICS NODES ──
    path('logistics/attendance-deck/', views.global_attendance_control_deck, name='attendance_deck'),
    path('logistics/inventory/', views.inventory_asset_control_deck, name='inventory_deck'),
]