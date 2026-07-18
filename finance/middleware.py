# finance/middleware.py
"""
Role-based access control.

Only the system OWNER (Django superuser — the admin account) may open the
administrative / finance / operations / staff sections. Every other logged-in
user (headteacher, teacher, bursar, support) is restricted to the shared
Learners / Attendance / Academics areas.

Adjust OWNER_ONLY below to widen or narrow access per role.
"""
from django.shortcuts import redirect
from django.contrib import messages

# URL route names that only the owner (superuser) may access.
# Everything else (Learners add/edit, Attendance, Academics, Finance data entry)
# is available to staff (headteacher / teacher) for day-to-day data entry.
OWNER_ONLY = {
    # Executive / overview
    'executive_kpis',
    # Sensitive finance (ledger, structure, defaulters, analytics, reports)
    'bursar_dashboard',
    'bulk_balance_import',
    'fee_structure',
    'fee_defaulters_portal',
    'financial_analytics',
    'invoice_list',
    'generate_invoice_pdf',
    'teacher_sms_broadcast',
    'finance_reports',
    'export_report_csv',
    'generate_bulk_invoices',
    # Analytics / reports
    'academic_analytics',
    'generate_report_card',
    # Staff administration (HR)
    'staff_management_matrix',
    'faculty_directory',
    'staff_create',
    'staff_edit',
    'leave_management',
    # Operations
    'grade_promotion',
    'inventory_deck',
}


class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated:
            return None
        url_name = request.resolver_match.url_name if request.resolver_match else None
        if url_name in OWNER_ONLY and not request.user.is_superuser:
            messages.error(
                request,
                "Access denied: only the system owner can open that section."
            )
            return redirect('academic_hub')
        return None
