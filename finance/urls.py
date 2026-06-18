# finance/urls.py
from django.urls import path
from finance import views

urlpatterns = [
    # ── CORE ACCESSIBLE WEB CHANNELS ──
    path('', views.bursar_dashboard, name='public_home'),
    
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
    path('treasury/fee-structure/', views.fee_structure, name='fee_structure'),
    path('treasury/statement/<int:student_id>/', views.student_account_statement, name='student_statement'),
    path('treasury/collect-fees/<int:student_id>/', views.collect_fee_payment, name='collect_fee_payment'),
    path('treasury/defaulters-sms/', views.fee_defaulters_portal, name='fee_defaulters_portal'),
    path('treasury/analytics/', views.financial_analytics, name='financial_analytics'),
    path('treasury/invoices/', views.invoice_list, name='invoice_list'),
    path('treasury/invoice/<int:invoice_id>/pdf/', views.generate_invoice_pdf, name='generate_invoice_pdf'),
    
    # ── FACULTY BROADCASTER ENGINE ──
    path('faculty/class-broadcast/', views.teacher_sms_broadcast, name='teacher_sms_broadcast'),

    # ── ACADEMIC EVALUATION WORKSPACE ──
    path('academic/management-hub/', views.academic_management_hub, name='academic_hub'),
    path('academic/grading-desk/', views.marks_entry_portal, name='marks_entry_portal'),
    path('academic/analytics/', views.academic_analytics_dashboard, name='academic_analytics'),
    path('academic/report-card/<int:student_id>/pdf/', views.generate_report_card_view, name='generate_report_card'),
    path('academic/post-homework/', views.post_homework_assignment, name='post_homework'),
    
    # ── EXTERNAL PARENT GATEWAY SYSTEM ──
    path('parent-portal/', views.parent_portal_gateway, name='parent_portal_gateway'),
    
    # ── ROUTINE ASSET LOGISTICS NODES & ATTENDANCE TRACKERS ──
    path('logistics/attendance-deck/', views.global_attendance_control_deck, name='attendance_deck'),
    
    # 🎯 FIXED: These two critical lines are now restored back into your application!
    path('attendance/daily-deck/', views.daily_attendance_deck, name='daily_attendance_deck'),
    path('attendance/commit-bulk-attendance/', views.commit_bulk_attendance, name='commit_bulk_attendance'),
    
    path('logistics/inventory/', views.inventory_asset_control_deck, name='inventory_deck'),

    # ── STUDENT OPERATIONAL DIRECTORY ──
    path('registry/learners/', views.student_registry_workstation, name='student_registry'),
    path('registry/learners/<int:student_id>/folder/', views.single_student_profile_folder, name='student_profile'),
    
    # 🎯 FIXED: Maps the modal onboarding form submission directly to the view function!
    path('add-new-student-onboarding/', views.add_new_student_onboarding, name='add_new_student_onboarding'),
    
    path('registry/staff-matrix/', views.staff_management_matrix, name='staff_management_matrix'),
    path('registry/faculty/', views.faculty_directory, name='faculty_directory'),

    # Place these inside your urlpatterns list alongside other student routes
    path('registry/learners/<int:student_id>/edit/', views.edit_student_info, name='edit_student'),
    path('registry/learners/<int:student_id>/delete/', views.delete_student_record, name='delete_student'),
    path('registry/grade-promotion/', views.grade_promotion_dashboard, name='grade_promotion'),
    
    # ── REPORT HUB & EXPORT ENGINE ──
    path('reports/', views.finance_reports_hub, name='finance_reports'),
    path('reports/export/<str:report_type>/csv/', views.export_report_csv, name='export_report_csv'),
    path('reports/generate-invoices/', views.generate_bulk_invoices, name='generate_bulk_invoices'),
]