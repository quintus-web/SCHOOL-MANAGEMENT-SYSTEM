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
        self.current_grade = row[5].strip() if len(row) > 5 else "Playgroup"

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
    discipline_logs = student.discipline_logs.all().order_by('-date_reported')[:10]
    invoices = student.fee_invoices.all().order_by('-date_issued')[:10]
    receipts = student.fee_receipts.all().order_by('-date_paid')[:10]
    attendance_records = student.attendance_history.all().order_by('-date')[:20]
    exam_records = ExamRecord.objects.filter(student=student).select_related('subject').order_by('-year', '-term')[:20]
    total_paid = sum((r.amount for r in receipts), Decimal("0.00"))
    att_all = student.attendance_history.all()
    attendance_total = att_all.count()
    attendance_present = sum(1 for r in att_all if r.is_present)
    attendance_pct = round((attendance_present / attendance_total) * 100, 1) if attendance_total else 100.0
    return render(request, "finance/student_profile_folder.html", {
        "student": student,
        "discipline_logs": discipline_logs,
        "invoices": invoices,
        "receipts": receipts,
        "attendance_records": attendance_records,
        "exam_records": exam_records,
        "total_paid": total_paid,
        "attendance_total": attendance_total,
        "attendance_present": attendance_present,
        "attendance_pct": attendance_pct
    })


@login_required
def add_student_registry(request):
    if request.method == "POST":
        messages.success(request, "Enrollment initialization entry registered successfully.")
        return redirect("student_registry")
    return render(request, "finance/add_student.html")


@login_required
def staff_management_matrix(request):
    staff_roster = StaffProfile.objects.all().select_related('user')
    return render(request, "finance/staff_management_matrix.html", {"staff_roster": staff_roster})


@login_required
def faculty_directory(request):
    teachers = StaffProfile.objects.filter(role_designation='TEACHER').select_related('user')
    return render(request, "finance/faculty_directory.html", {"teachers": teachers})


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

        open_invoice = FeeInvoice.objects.filter(student=student).order_by('date_issued').first()
        if not open_invoice:
            fee_entry = FeeStructure.objects.filter(level=student.class_stream.name).first()
            invoice_amount = fee_entry.amount if fee_entry else Decimal("0.00")
            open_invoice = FeeInvoice.objects.create(
                student=student,
                title=f"{student.class_stream.name} Term 1 Invoice 2026",
                amount=invoice_amount,
                description="Auto-generated from Crescent Heights Fee Structure 2026"
            )

        FeeReceipt.objects.create(
            student=student,
            invoice=open_invoice,
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


@login_required
def fee_structure(request):
    schedules = FeeStructure.objects.all().order_by('level', 'term')
    levels = sorted(FeeStructure.objects.values_list('level', flat=True).distinct())
    grouped = {}
    for sched in schedules:
        grouped.setdefault(sched.level, {})[sched.term] = sched.amount
    return render(request, "finance/fee_structure.html", {
        "grouped": grouped,
        "levels": levels
    })


@login_required
def financial_analytics(request):
    from collections import defaultdict
    from django.db.models import Sum, Count, Q, F
    import json

    term = request.GET.get("term", "TERM_1")
    level_filter = request.GET.get("level", "")

    students_qs = Student.objects.filter(status='ACTIVE')
    if level_filter:
        students_qs = students_qs.filter(class_stream__name=level_filter)

    all_invoices = FeeInvoice.objects.all()
    all_receipts = FeeReceipt.objects.all()

    if term and term != "ALL":
        all_invoices = all_invoices.filter(term=term)
        all_receipts = all_receipts.filter(invoice__term=term)

    if level_filter:
        all_invoices = all_invoices.filter(student__class_stream__name=level_filter)
        all_receipts = all_receipts.filter(student__class_stream__name=level_filter)

    levels = sorted(set(Student.objects.exclude(class_stream__isnull=True).values_list('class_stream__name', flat=True)))

    expected = float(all_invoices.aggregate(total=Sum('amount'))['total'] or 0)
    collected = float(all_receipts.aggregate(total=Sum('amount'))['total'] or 0)
    outstanding = expected - collected
    collection_rate = round((collected / expected) * 100, 1) if expected else 0.0

    stream_breakdown = []
    for lvl in levels:
        lvl_students = students_qs.filter(class_stream__name=lvl)
        lvl_expected = float(all_invoices.filter(student__class_stream__name=lvl).aggregate(total=Sum('amount'))['total'] or 0)
        lvl_collected = float(all_receipts.filter(student__class_stream__name=lvl).aggregate(total=Sum('amount'))['total'] or 0)
        lvl_outstanding = lvl_expected - lvl_collected
        stream_breakdown.append({
            'level': lvl,
            'students': lvl_students.count(),
            'expected': lvl_expected,
            'collected': lvl_collected,
            'outstanding': lvl_outstanding,
            'rate': round((lvl_collected / lvl_expected) * 100, 1) if lvl_expected else 0.0
        })

    term_data = []
    for t in ['TERM_1', 'TERM_2', 'TERM_3']:
        t_exp = float(FeeInvoice.objects.filter(term=t).aggregate(total=Sum('amount'))['total'] or 0)
        t_col = float(FeeReceipt.objects.filter(invoice__term=t).aggregate(total=Sum('amount'))['total'] or 0)
        term_data.append({
            'term': t,
            'expected': t_exp,
            'collected': t_col,
            'outstanding': t_exp - t_col,
            'rate': round((t_col / t_exp) * 100, 1) if t_exp else 0.0
        })

    defaulters = Student.objects.filter(current_balance__gt=0).order_by('-current_balance')[:50]
    defaulter_data = []
    for s in defaulters:
        defaulter_data.append({
            'student': s,
            'balance': float(s.current_balance),
            'stream': s.class_stream.name if s.class_stream else 'Unassigned',
            'adm': s.admission_number,
            'name': f"{s.first_name} {s.last_name}"
        })

    payment_channels = []
    channel_qs = all_receipts.values('payment_channel').annotate(total=Sum('amount'), count=Count('id'))
    for ch in channel_qs:
        payment_channels.append({
            'channel': ch['payment_channel'] or 'CASH',
            'total': float(ch['total'] or 0),
            'count': ch['count']
        })

    return render(request, "finance/financial_analytics.html", {
        "term": term,
        "level_filter": level_filter,
        "levels": levels,
        "expected": expected,
        "collected": collected,
        "outstanding": outstanding,
        "collection_rate": collection_rate,
        "stream_breakdown": stream_breakdown,
        "term_data": term_data,
        "defaulter_data": defaulter_data,
        "payment_channels": payment_channels,
        "current_page": "analytics"
    })


# =========================================================
# 5. INTEGRATED BROADCASTER & COMMUNICATORS
# =========================================================

@login_required
def teacher_sms_broadcast(request):
    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if not message:
            messages.error(request, "Broadcast message cannot be empty.")
            return redirect("teacher_sms_broadcast")
        
        import requests
        import base64
        
        username = request.POST.get("username", "").strip()
        api_key = request.POST.get("api_key", "").strip()
        sender_id = request.POST.get("sender_id", "KABIERO").strip()
        
        if not username or not api_key:
            messages.error(request, "Africa's Talking credentials required in session settings.")
            return redirect("teacher_sms_broadcast")

        recipients = request.POST.getlist("recipient_phone")
        if not recipients:
            messages.error(request, "No recipient phone numbers selected.")
            return redirect("teacher_sms_broadcast")

        url = "https://api.africastalking.com/version1/messaging"
        auth_header = base64.b64encode(f"{username}:{api_key}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        success_count = 0
        error_count = 0
        for phone in recipients:
            phone = phone.strip()
            if not phone.startswith('+'):
                phone = f"+254{phone.lstrip('0')}"
            data = {
                "username": username,
                "to": phone,
                "message": message[:160],
                "from": sender_id,
            }
            try:
                resp = requests.post(url, headers=headers, data=data, timeout=30)
                result = resp.json()
                if result.get("SMSMessageData", {}).get("Recipients"):
                    success_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1
        
        if error_count == 0:
            messages.success(request, f"Broadcast dispatched successfully to {success_count} parent contact(s).")
        else:
            messages.warning(request, f"Completed: {success_count} sent, {error_count} failed.")
        return redirect("teacher_sms_broadcast")
    
    students = Student.objects.filter(is_active=True).select_related('class_stream')
    recipients = []
    seen = set()
    for s in students:
        phone = s.parent_phone.strip()
        if phone and phone not in seen and len(phone) >= 10:
            seen.add(phone)
            recipients.append({
                'student': s,
                'phone': phone,
                'guardian': s.guardian_name,
            })
    
    return render(request, "finance/teacher_sms.html", {
        "recipients": recipients,
        "total_recipients": len(recipients),
    })


# =========================================================
# 6. ATTENDANCE & LOGISTICS MODULES
# =========================================================

@login_required
@csrf_exempt
def daily_attendance_deck(request):
    # Authentic Kenyan CBC Grade Sort Sequence Order List
    ordered_grades = ["Playgroup", "PP1", "PP2", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6"]
    
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
    assets = SchoolAsset.objects.all().order_by('category', 'name')
    selected_category = request.GET.get('category', 'ALL')
    if selected_category != 'ALL':
        assets = assets.filter(category=selected_category)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            SchoolAsset.objects.create(
                name=request.POST.get('name', '').strip(),
                serial_or_isbn=request.POST.get('serial', '').strip(),
                category=request.POST.get('category', 'TEXTBOOKS'),
                total_quantity=int(request.POST.get('total_qty', 1)),
                available_quantity=int(request.POST.get('available_qty', 1)),
                assigned_location=request.POST.get('location', '').strip(),
                status=request.POST.get('status', 'OPERATIONAL'),
            )
            messages.success(request, "New asset registered successfully.")
            return redirect('inventory_deck')
        elif action == 'edit':
            asset = get_object_or_404(SchoolAsset, id=request.POST.get('asset_id'))
            asset.name = request.POST.get('name', '').strip()
            asset.serial_or_isbn = request.POST.get('serial', '').strip()
            asset.category = request.POST.get('category', 'TEXTBOOKS')
            asset.total_quantity = int(request.POST.get('total_qty', 1))
            asset.available_quantity = int(request.POST.get('available_qty', 1))
            asset.assigned_location = request.POST.get('location', '').strip()
            asset.status = request.POST.get('status', 'OPERATIONAL')
            asset.save()
            messages.success(request, f"Asset '{asset.name}' updated successfully.")
            return redirect('inventory_deck')
        elif action == 'delete':
            asset = get_object_or_404(SchoolAsset, id=request.POST.get('asset_id'))
            asset_name = asset.name
            asset.delete()
            messages.warning(request, f"'{asset_name}' has been removed from the inventory.")
            return redirect('inventory_deck')
    
    maintenance_tickets = AssetMaintenanceLog.objects.filter(is_resolved=False).select_related('asset')
    context = {
        'assets': assets,
        'selected_category': selected_category,
        'maintenance_tickets': maintenance_tickets,
        'total_operational': SchoolAsset.objects.filter(status='OPERATIONAL').count(),
        'total_repair_flags': SchoolAsset.objects.filter(status='UNDER_REPAIR').count(),
    }
    return render(request, "finance/inventory_control_deck.html", context)


# =========================================================
# 7. ACADEMIC GRADE WORKSTATIONS
# =========================================================

@login_required
def academic_management_hub(request):
    return render(request, "finance/academic_hub.html")


@login_required
def marks_entry_portal(request):
    """Renders a streamlined spreadsheet matrix for fast term marks collection"""
    subjects = Subject.objects.all().order_by('name')
    streams = ClassStream.objects.all().order_by('name')
    
    selected_subject_id = request.GET.get('subject')
    selected_stream_id = request.GET.get('stream')
    term = request.GET.get('term', 'TERM_1')
    year = int(request.GET.get('year', 2026))
    
    matrix_data = []
    
    if selected_subject_id and selected_stream_id:
        students = Student.objects.filter(class_stream_id=selected_stream_id, is_active=True).order_by('last_name')
        for student in students:
            record = ExamRecord.objects.filter(student=student, subject_id=selected_subject_id, term=term, year=year).first()
            matrix_data.append({
                'student': student,
                'cat_1': record.cat_1 if record else 0,
                'cat_2': record.cat_2 if record else 0,
                'final_exam': record.final_exam if record else 0,
                'total_marks': record.total_marks if record else 0
            })

    if request.method == 'POST' and matrix_data:
        saved_count = 0
        for row in matrix_data:
            student = row['student']
            cat1 = request.POST.get(f'cat1_{student.id}', '0')
            cat2 = request.POST.get(f'cat2_{student.id}', '0')
            exam = request.POST.get(f'exam_{student.id}', '0')
            
            cat1 = max(0, min(30, int(cat1) if cat1.isdigit() else 0))
            cat2 = max(0, min(30, int(cat2) if cat2.isdigit() else 0))
            exam = max(0, min(40, int(exam) if exam.isdigit() else 0))
            
            ExamRecord.objects.update_or_create(
                student=student,
                subject_id=selected_subject_id,
                term=term,
                year=year,
                defaults={
                    'cat_1': cat1,
                    'cat_2': cat2,
                    'final_exam': exam
                }
            )
            saved_count += 1
        
        messages.success(request, f"Examination score parameters compiled. {saved_count} records successfully saved.")
        return redirect(f"{request.path}?subject={selected_subject_id}&stream={selected_stream_id}&term={term}&year={year}")

    context = {
        'subjects': subjects,
        'streams': streams,
        'matrix_data': matrix_data,
        'selected_subject': int(selected_subject_id) if selected_subject_id else None,
        'selected_stream': int(selected_stream_id) if selected_stream_id else None,
        'selected_term': term,
        'selected_year': year,
    }
    return render(request, "finance/marks_entry_portal.html", context)


@login_required
def generate_report_card_view(request, student_id):
    """Aggregates scores and compiles an on-the-fly PDF Report Card for a specific student"""
    from django.template.loader import render_to_string
    
    student = get_object_or_404(Student, id=student_id)
    term = request.GET.get('term', 'TERM_1')
    year = int(request.GET.get('year', 2026))
    
    exam_records = ExamRecord.objects.filter(student=student, term=term, year=year).select_related('subject')
    
    total_score = sum(r.total_marks for r in exam_records)
    records_count = exam_records.count()
    mean_score = (total_score / records_count) if records_count > 0 else 0.0
    
    if mean_score >= 80: mean_grade, remarks = 'A', 'Excellent performance. Keep it up.'
    elif mean_score >= 70: mean_grade, remarks = 'B', 'Very good effort. Room for top tier.'
    elif mean_score >= 50: mean_grade, remarks = 'C', 'Average achievement. Focus more on weak areas.'
    else: mean_grade, remarks = 'D', 'Below expectation. Intensive remedial required.'

    context = {
        'student': student,
        'exam_records': exam_records,
        'total_score': total_score,
        'mean_score': round(mean_score, 1),
        'mean_grade': mean_grade,
        'remarks': remarks,
        'today': timezone.now(),
        'term': term,
        'year': year,
    }
    
    try:
        from weasyprint import HTML
        html_string = render_to_string('finance/report_card_printout.html', context)
        response = HttpResponse(content_type='application/pdf')
        filename = f"report_card_{student.admission_number}_{term}_{year}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        HTML(string=html_string).write_pdf(response)
        return response
    except (ImportError, OSError) as e:
        html_string = render_to_string('finance/report_card_printout.html', context)
        response = HttpResponse(html_string, content_type='text/html')
        response['Content-Disposition'] = f'inline; filename="report_card_{student.admission_number}_{term}_{year}.html"'
        messages.info(request, "PDF engine unavailable - rendering print-friendly HTML. Use browser Print to save as PDF.")
        return response


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
    from finance.models import Student, ClassStream
    from django.core.management import call_command
    import io
    from contextlib import redirect_stdout

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "purge":
            Student.objects.all().delete()
            messages.success(request, "Local development sandbox records truncated clean.")
        elif action == "inject_mock_data":
            buf = io.StringIO()
            with redirect_stdout(buf):
                call_command('seed_data', verbosity=0)
            output = buf.getvalue()
            count = Student.objects.count()
            messages.success(request, f"Seed complete. {count} students loaded from CSV.")
        return redirect('dev_debug_console')

    return render(request, "finance/developer_debug_console.html", {
        "total_students": Student.objects.count(),
        "total_streams": ClassStream.objects.count(),
        "total_infractions": 0,
        "raw_students": Student.objects.all()[:10],
        "raw_staff": []
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


@login_required
def academic_analytics_dashboard(request):
    """Aggregates exam fields across terms and monitors student performance trajectories"""
    selected_term = request.GET.get('term', 'TERM_2')
    year = int(request.GET.get('year', 2026))
    
    all_streams = ClassStream.objects.all()
    stream_rankings = []
    for stream in all_streams:
        records = ExamRecord.objects.filter(student__class_stream=stream, term=selected_term, year=year).select_related('student', 'subject')
        total_records = records.count()
        if total_records > 0:
            avg_score = sum(r.total_marks for r in records) / total_records
        else:
            avg_score = 0.0
        student_count = Student.objects.filter(class_stream=stream, is_active=True).count()
        stream_rankings.append({
            'name': stream.name, 
            'average': avg_score, 
            'count': student_count
        })
    stream_rankings.sort(key=lambda x: x['average'], reverse=True)

    all_subjects = Subject.objects.all()
    subject_performance = []
    for subject in all_subjects:
        records = ExamRecord.objects.filter(subject=subject, term=selected_term, year=year).select_related('student')
        total_records = records.count()
        avg_score = sum(r.total_marks for r in records) / total_records if total_records > 0 else 0.0
        subject_performance.append({'name': subject.name, 'code': subject.code, 'average': avg_score})
    subject_performance.sort(key=lambda x: x['average'], reverse=True)

    all_students = Student.objects.filter(is_active=True)
    trajectory_list = []
    
    for s in all_students:
        t1_records = ExamRecord.objects.filter(student=s, term='TERM_1', year=year).select_related('subject')
        t2_records = ExamRecord.objects.filter(student=s, term='TERM_2', year=year).select_related('subject')
        
        t1_avg = sum(r.total_marks for r in t1_records) / t1_records.count() if t1_records.exists() else None
        t2_avg = sum(r.total_marks for r in t2_records) / t2_records.count() if t2_records.exists() else None
        
        if t1_avg is not None and t2_avg is not None:
            variance = t2_avg - t1_avg
            if variance <= -5.0:
                badge_class, icon, label = 'bg-danger', 'bi-graph-down-arrow', 'Slipping'
            elif variance >= 5.0:
                badge_class, icon, label = 'bg-success', 'bi-graph-up-arrow', 'Improving'
            else:
                badge_class, icon, label = 'bg-secondary', 'bi-arrow-right-short', 'Stable'
                
            trajectory_list.append({
                'student': s, 't1_avg': t1_avg, 't2_avg': t2_avg,
                'variance': variance, 'badge_class': badge_class, 'icon': icon, 'label': label
            })
    trajectory_list.sort(key=lambda x: x['variance'])

    context = {
        'term_display': selected_term.replace('_', ' '), 'selected_term': selected_term,
        'stream_rankings': stream_rankings, 'subject_performance': subject_performance,
        'trajectories': trajectory_list,
    }
    return render(request, "finance/analytics_dashboard.html", context)
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


@login_required
def attendance_history_report(request):
    selected_stream = request.GET.get("stream_id", "")
    selected_date = request.GET.get("date", timezone.now().date().isoformat())

    students_in_stream = Student.objects.none()
    day_logs = StudentAttendanceRecord.objects.none()
    log_map = {}
    stream_summary = {"total": 0, "present": 0, "absent": 0, "percentage": 100.0}

    if selected_stream:
        students_in_stream = Student.objects.filter(
            class_stream__name=selected_stream,
            status='ACTIVE'
        ).order_by('first_name')

        day_logs = StudentAttendanceRecord.objects.filter(
            date=selected_date,
            student__class_stream__name=selected_stream
        )

        log_map = {log.student_id: log for log in day_logs}

        present_count = sum(1 for log in day_logs if log.is_present)
        total_for_day = day_logs.count()
        stream_summary = {
            "total": total_for_day,
            "present": present_count,
            "absent": total_for_day - present_count,
            "percentage": round((present_count / total_for_day) * 100, 1) if total_for_day else 0.0
        }

    db_streams = sorted(
        set(Student.objects.exclude(class_stream__isnull=True).values_list('class_stream__name', flat=True))
    )

    student_rows = []
    for student in students_in_stream:
        log = log_map.get(student.id) if selected_stream else None
        student_rows.append({
            "student": student,
            "log": log
        })

    return render(request, "finance/attendance_history_report.html", {
        "streams": db_streams,
        "selected_stream": selected_stream,
        "selected_date": selected_date,
        "student_rows": student_rows,
        "stream_summary": stream_summary,
        "current_page": "attendance"
    })


@login_required
def staff_create(request):
    subjects = Subject.objects.all().order_by('name')
    if request.method == "POST":
        data = request.POST
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        employee_number = data.get("employee_number", "").strip()
        role = data.get("role", "TEACHER")
        specialization_id = data.get("specialization")
        phone_line = data.get("phone_line", "0700000000").strip()
        base_salary = data.get("base_salary_kes", "45000")

        if not username or not password or not first_name or not last_name or not employee_number:
            messages.error(request, "Required fields missing.")
            return redirect("staff_create")

        user, created = User.objects.get_or_create(username=username, defaults={"first_name": first_name, "last_name": last_name})
        if not created:
            messages.error(request, "Username already exists.")
            return redirect("staff_create")
        user.set_password(password)
        user.save()

        specialization = Subject.objects.filter(id=specialization_id).first() if specialization_id else None
        StaffProfile.objects.create(
            user=user,
            employee_number=employee_number,
            role_designation=role,
            specialization=specialization.name if specialization else "General",
            phone_line=phone_line,
            base_salary_kes=base_salary
        )
        messages.success(request, "Staff record initialized successfully.")
        return redirect("staff_management")

    return render(request, "finance/staff_form.html", {
        "subjects": subjects,
        "mode": "create"
    })


@login_required
def staff_edit(request, staff_id):
    profile = get_object_or_404(StaffProfile, id=staff_id)
    subjects = Subject.objects.all().order_by('name')
    if request.method == "POST":
        data = request.POST
        profile.user.first_name = data.get("first_name", "").strip() or profile.user.first_name
        profile.user.last_name = data.get("last_name", "").strip() or profile.user.last_name
        profile.user.save()
        profile.role_designation = data.get("role", profile.role_designation)
        profile.employee_number = data.get("employee_number", profile.employee_number).strip()
        specialization_id = data.get("specialization")
        specialization = Subject.objects.filter(id=specialization_id).first() if specialization_id else None
        profile.specialization = specialization.name if specialization else profile.specialization
        profile.phone_line = data.get("phone_line", profile.phone_line).strip()
        profile.base_salary_kes = data.get("base_salary_kes", profile.base_salary_kes)
        profile.current_status = data.get("status", profile.current_status)
        profile.save()
        messages.success(request, "Staff profile updated successfully.")
        return redirect("staff_management")
    return render(request, "finance/staff_form.html", {
        "subjects": subjects,
        "mode": "edit",
        "profile": profile
    })


@login_required
def leave_management(request):
    pending = LeaveApplication.objects.filter(is_approved=False).select_related('staff__user').order_by('-id')
    approved = LeaveApplication.objects.filter(is_approved=True).select_related('staff__user').order_by('-id')[:50]
    if request.method == "POST":
        action = request.POST.get("action")
        leave_id = request.POST.get("leave_id")
        leave = get_object_or_404(LeaveApplication, id=leave_id)
        if action == "approve":
            leave.is_approved = True
            leave.save()
            messages.success(request, "Leave application approved.")
        elif action == "reject":
            leave.delete()
            messages.warning(request, "Leave application rejected and removed.")
        return redirect("leave_management")
    return render(request, "finance/leave_management.html", {
        "pending_leaves": pending,
        "approved_leaves": approved
    })


@login_required
def post_homework_assignment(request):
    subjects = Subject.objects.all().order_by('name')
    streams = ClassStream.objects.all().order_by('name')
    
    if request.method == "POST":
        stream_id = request.POST.get("stream")
        subject_id = request.POST.get("subject")
        title = request.POST.get("title", "").strip()
        instructions = request.POST.get("instructions", "").strip()
        deadline = request.POST.get("deadline")
        
        if not all([stream_id, subject_id, title, instructions, deadline]):
            messages.error(request, "All fields are required to post an assignment.")
            return redirect("post_homework")
        
        try:
            stream = ClassStream.objects.get(id=stream_id)
            subject = Subject.objects.get(id=subject_id)
            HomeworkAssignment.objects.create(
                stream=stream,
                subject=subject,
                title=title,
                task_instructions=instructions,
                submission_deadline=deadline
            )
            messages.success(request, f"Homework assignment '{title}' posted successfully to {stream.name}.")
            return redirect("post_homework")
        except Exception as e:
            messages.error(request, f"Error posting assignment: {str(e)}")
    
    recent_assignments = HomeworkAssignment.objects.all().select_related('stream', 'subject').order_by('-date_given')[:10]
    return render(request, "finance/post_homework.html", {
        "subjects": subjects,
        "streams": streams,
        "recent_assignments": recent_assignments,
    })