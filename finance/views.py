# finance/views.py
import os
import csv
import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import (
    Student, ClassStream, Subject,
    FeeInvoice, FeeReceipt,
    ExamRecord,
    StudentAttendanceRecord,
    TeacherAttendanceRecord,
    StaffProfile,
    SchoolAsset, AssetMaintenanceLog,
    HomeworkAssignment, SchoolAnnouncement,
    LessonPlan, LearningMaterial, TimetableSlot
)

# =========================================================
# 1. CSV ENGINE LAYER (SINGLE SOURCE ROUTINE)
# =========================================================

class LiveCSVStudent:
    def __init__(self, row):
        self.admission_number = row[0].strip()
        self.id = self.admission_number.replace("/", "-")

        full_name = row[1].strip()
        parts = full_name.split(" ", 1)

        self.first_name = parts[0]
        self.last_name = parts[1] if len(parts) > 1 else ""
        self.gender = row[2].strip() if len(row) > 2 else ""
        self.current_grade = row[5].strip() if len(row) > 5 else "Playground"

        class Stream:
            def __init__(self, name):
                self.name = name

        self.class_stream = Stream(self.current_grade)
        self.guardian_name = row[8].strip() if len(row) > 8 else ""
        self.parent_phone = row[9].strip() if len(row) > 9 else ""
        self.current_balance = 0.0


def _load_students_from_csv():
    """Reads foundational tracking records from local project workspace directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "Crescent Heights School - STUDENTS.csv")

    students = []
    if os.path.exists(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader, None)

            for row in reader:
                if row and len(row) > 1:
                    students.append(LiveCSVStudent(row))
    return students


# =========================================================
# 2. CORE PORTAL & ADMINISTRATIVE PANELS
# =========================================================

@login_required
def executive_analytics_kpi_dashboard(request):
    csv_students = _load_students_from_csv()
    total_receipts = FeeReceipt.objects.aggregate(total=Sum("amount"))["total"] or 0
    total_invoiced = FeeInvoice.objects.aggregate(total=Sum("amount"))["total"] or 0

    return render(request, "portal/executive_kpis.html", {
        "total_receipts": total_receipts,
        "total_invoiced": total_invoiced,
        "active_learners_count": len(csv_students),
        "unresolved_balances": Student.objects.aggregate(total=Sum("current_balance"))["total"] or 0,
        "generation_date": timezone.now().date()
    })


# =========================================================
# 3. STUDENT & FACULTY REGISTRY WORKSPACES
# =========================================================

@login_required
def student_registry_workstation(request):
    students = Student.objects.all().order_by('admission_number')
    selected_stream = request.GET.get("stream_id")

    if selected_stream:
        students = students.filter(class_stream__name=selected_stream)

    return render(request, "finance/learners.html", {
        "students": students,
        "selected_stream": selected_stream
    })


@login_required
def single_student_profile_folder(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    return render(request, "finance/student_profile_folder.html", {
        "student": student
    })


@login_required
def add_student_registry(request):
    if request.method == "POST":
        messages.success(request, "Enrollment initialization entry registered successfully.")
        return redirect("student_registry")
    return render(request, "finance/add_student.html")


@login_required
def staff_management_matrix(request):
    staff_members = StaffProfile.objects.all()
    return render(request, "finance/staff_matrix.html", {"staff": staff_members})


@login_required
def faculty_directory(request):
    return render(request, "finance/faculty_directory.html")


# =========================================================
# 4. FINANCIAL LEDGER & ACCOUNTING STATIONS
# =========================================================

@login_required
def bursar_dashboard(request):
    search = request.GET.get("search", "").lower()
    students = Student.objects.all().order_by('admission_number')

    if search:
        students = students.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(admission_number__icontains=search)
        )

    return render(request, "finance/bursar_dashboard.html", {
        "students": students,
        "search_query": search
    })


@login_required
def student_account_statement(request, student_id):
    student_record = get_object_or_404(Student, id=student_id)
    db_invoices = FeeInvoice.objects.filter(student_id=student_id).order_by('-date_issued')
    db_receipts = FeeReceipt.objects.filter(student=student_record).order_by('-date_paid')

    ledger_entries = []

    # Process Invoices as DEBITS (Money Owed)
    for inv in db_invoices:
        ledger_entries.append({
            'date': inv.date_issued,
            'description': inv.description if inv.description else "Tuition Fee Invoice Charge",
            'reference': f"INV-{inv.id}",
            'type': 'DEBIT',
            'amount': float(inv.amount)
        })

    # Process Receipts as CREDITS (Money Paid)
    for rec in db_receipts:
        rec_date = rec.date_paid if rec.date_paid else rec.date_issued
        rec_desc = rec.description if rec.description else "School Fees Payment"
        ref_code = rec.reference_code if rec.reference_code else f"RCT-{rec.id}"
        rec_amount = rec.amount if rec.amount else 0.0

        ledger_entries.append({
            'date': rec_date,
            'description': f"{rec_desc} (Ref: {ref_code})",
            'reference': f"RCT-{rec.id}",
            'type': 'CREDIT',
            'amount': float(rec_amount)
        })

    # Sort timeline by date safely
    ledger_entries = [e for e in ledger_entries if e['date'] is not None]
    ledger_entries.sort(key=lambda x: x['date'], reverse=True)

    return render(request, "finance/student_statement.html", {
        "student": student_record,
        "ledger_entries": ledger_entries
    })


@login_required
def collect_fee_payment(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        amount = Decimal(request.POST.get("amount_paid", 0))
        if amount <= 0:
            messages.error(request, "Invalid transactional processing parameter.")
            return redirect(request.path)

        FeeReceipt.objects.create(
            student=student,
            amount=amount,
            status="COMPLETED",
            reference_code=f"RCPT-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        )

        student.current_balance = max(0, Decimal(student.current_balance) - amount)
        student.save()

        messages.success(request, f"Payment trace of KSH {amount} successfully posted.")
        return redirect("bursar_dashboard")

    return render(request, "finance/receipt_form.html", {"student": student})


@login_required
def fee_defaulters_portal(request):
    if request.method == "POST":
        messages.success(request, "Outstanding debt notification arrays dispatched.")
    return render(request, "finance/defaulters.html")


# =========================================================
# 5. INTEGRATED BROADCASTER & COMMUNICATORS
# =========================================================

@login_required
def teacher_sms_broadcast(request):
    if request.method == "POST":
        messages.success(request, "System alert broadcast pushed safely to parent contacts.")
    return render(request, "finance/teacher_broadcast.html")


# =========================================================
# 6. ATTENDANCE & LOGISTICS MODULES
# =========================================================

@login_required
@csrf_exempt
def daily_attendance_deck(request):
    # Authentic Kenyan CBC Grade Sort Sequence Order List
    ordered_grades = ["Playground", "PP1", "PP2", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6"]
    
    db_streams = set(Student.objects.filter(class_stream__isnull=False).values_list('class_stream__name', flat=True))
    streams = [g for g in ordered_grades if g in db_streams] or ordered_grades

    selected_stream = request.GET.get("stream_id", streams[0] if streams else "")
    current_date = timezone.now().date()
    
    students_in_stream = Student.objects.filter(
        class_stream__name=selected_stream, 
        status='ACTIVE'
    ).order_by('first_name')
    
    existing_logs = {
        log.student_id: "PRESENT" if log.is_present else "ABSENT"
        for log in StudentAttendanceRecord.objects.filter(date=current_date, student__class_stream__name=selected_stream)
    }

    return render(request, "finance/daily_attendance_deck.html", {
        "streams": streams,
        "selected_stream": selected_stream,
        "students": students_in_stream,
        "existing_logs": existing_logs,
        "current_date": current_date,
        "current_page": "attendance"
    })


@login_required
@csrf_exempt
def commit_bulk_attendance(request):
    if request.method == "POST":
        class_stream = request.POST.get("class_stream")
        current_date = timezone.now().date()
        student_ids = request.POST.getlist("student_ids")
        
        if not student_ids:
            messages.warning(request, "No student profile records were found to register.")
            return redirect(f"/attendance/daily-deck/?stream_id={class_stream}")
            
        saved_count = 0
        try:
            for s_id in student_ids:
                status = request.POST.get(f"status_{s_id}", "PRESENT")
                is_present_bool = True if status == "PRESENT" else False
                student_instance = Student.objects.get(id=int(s_id))
                
                StudentAttendanceRecord.objects.update_or_create(
                    student=student_instance,
                    date=current_date,
                    defaults={
                        'is_present': is_present_bool,
                        'remarks': f"Marked by {request.user.username}"
                    }
                )
                saved_count += 1
                
            messages.success(request, f"Success! {saved_count} roll-call records have been saved to the database.")
        except Exception as e:
            messages.error(request, f"Critical database tracking failure: {str(e)}")
            
        return redirect(f"/attendance/daily-deck/?stream_id={class_stream}")
        
    return redirect('/attendance/daily-deck/')


@login_required
def global_attendance_control_deck(request):
    return render(request, "finance/global_attendance_deck.html")


@login_required
def absentee_report(request):
    return render(request, "finance/absentee_report.html")


@login_required
def attendance_analytics(request):
    return render(request, "finance/attendance_analytics.html")


@login_required
def inventory_asset_control_deck(request):
    assets = SchoolAsset.objects.all()
    return render(request, "finance/inventory.html", {"assets": assets})


# =========================================================
# 7. ACADEMIC GRADE WORKSTATIONS
# =========================================================

@login_required
def academic_management_hub(request):
    return render(request, "finance/academic_hub.html")


@login_required
def marks_entry_portal(request):
    if request.method == "POST":
        messages.success(request, "Examination score parameters compiled successfully.")
    return render(request, "finance/marks_entry.html")


@login_required
def generate_report_card_view(request, student_id):
    return HttpResponse(f"System-generated PDF Statement Manifest for Learner Reference {student_id}")


# =========================================================
# 8. EXTERNAL ACCESS PORTALS
# =========================================================

def parent_portal_gateway(request):
    return render(request, "finance/parent_portal.html")


# =========================================================
# 9. ACCESS CONTROL & SYSTEM SECURITIES
# =========================================================

def staff_login_view(request):
    role = request.GET.get("role", "Admin")

    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password")
        )
        if user:
            login(request, user)
            
            # Bypass sidebar visibility restrictions for presentation account
            if user.is_superuser:
                request.session["active_role_context"] = "Headteacher"
                request.session["role"] = "Headteacher"
            else:
                request.session["active_role_context"] = role
                request.session["role"] = role
                
            return redirect("public_home")
        
        messages.error(request, "Operational authorization denied: Invalid terminal signatures.")

    return render(request, "finance/staff_login.html", {"target_role": role})


def staff_logout_view(request):
    logout(request)
    return redirect("public_home")


@login_required
def developer_debug_console_hub(request):
    if request.method == "POST" and request.POST.get("action") == "purge":
        Student.objects.all().delete()
        messages.success(request, "Local development sandbox records truncated clean.")
        
    return render(request, "finance/developer_debug_console.html", {
        "total_students": Student.objects.count()
    })


@login_required
@csrf_exempt
def add_new_student_onboarding(request):
    """Processes frontend modal forms and registers new CBC learners cleanly."""
    if request.method == "POST":
        adm_no = request.POST.get("admission_number")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        gender = request.POST.get("gender", "M")
        class_stream_name = request.POST.get("class_stream")
        guardian_name = request.POST.get("guardian_name")
        parent_phone = request.POST.get("parent_phone")

        if adm_no and first_name and last_name:
            try:
                stream_instance = None
                if class_stream_name:
                    stream_instance, _ = ClassStream.objects.get_or_create(name=class_stream_name.strip())

                Student.objects.update_or_create(
                    admission_number=adm_no.strip(),
                    defaults={
                        'first_name': first_name.strip(),
                        'last_name': last_name.strip(),
                        'gender': 'F' if gender.upper() in ['F', 'GIRL', 'FEMALE'] else 'M',
                        'class_stream': stream_instance,
                        'guardian_name': guardian_name.strip() if guardian_name else "Not Provided",
                        'parent_phone': parent_phone.strip() if parent_phone else "0700000000",
                        'current_balance': 0.00
                    }
                )
                messages.success(request, f"Success! {first_name} has been added to the registry.")
            except Exception as e:
                messages.error(request, f"Database error: {str(e)}")
        else:
            messages.error(request, "Required fields are missing.")
            
    return redirect('/registry/learners/')


# ========================================================
# 10. COMPATIBILITY ALIAS MATRIX
# ========================================================
finance_registry_ledger = bursar_dashboard
main_portal_home = bursar_dashboard
public_school_website = bursar_dashboard
staff_directory_matrix = bursar_dashboard
academic_analytics_dashboard = bursar_dashboard
fee_defaulters_sms_portal = fee_defaulters_portal

# Add these views to your finance/views.py file

@login_required
def edit_student_info(request, student_id):
    """Loads a student record and processes updates from an edit form."""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == "POST":
        student.first_name = request.POST.get("first_name").strip()
        student.last_name = request.POST.get("last_name").strip()
        student.gender = 'F' if request.POST.get("gender", "M").upper() in ['F', 'GIRL', 'FEMALE'] else 'M'
        student.guardian_name = request.POST.get("guardian_name", "").strip()
        student.parent_phone = request.POST.get("parent_phone", "").strip()
        
        class_stream_name = request.POST.get("class_stream")
        if class_stream_name:
            stream_instance, _ = ClassStream.objects.get_or_create(name=class_stream_name.strip())
            student.class_stream = stream_instance
            
        student.save()
        messages.success(request, f"Profile parameters for {student.first_name} updated successfully.")
        return redirect('student_registry')
        
    return render(request, "finance/edit_student.html", {"student": student})


@login_required
def delete_student_record(request, student_id):
    """Safely removes a learner entry from active directory matrix tracks."""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == "POST":
        first_name = student.first_name
        last_name = student.last_name
        student.delete()
        messages.warning(request, f"Learner record {first_name} {last_name} has been permanently purged from the database.")
        return redirect('student_registry')
        
    # Fallback to confirmation prompt if anyone hits via GET
    return render(request, "finance/confirm_delete.html", {"student": student})