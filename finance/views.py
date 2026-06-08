# finance/views.py
import datetime
import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .decorators import group_required

# Unified Model Imports matching production database architecture
from .models import (
    Teacher, ClassStream, Subject, Student, FeeInvoice, FeeReceipt, 
    ExamRecord, DisciplineReport, StaffProfile, HomeworkAssignment, 
    SchoolAnnouncement, StudentAttendanceRecord, TeacherAttendanceRecord,
    SchoolAsset, AssetMaintenanceLog, LessonPlan, LearningMaterial, TimetableSlot
)

# ==========================================
# 1. CORE ACCESSIBLE WEB CHANNELS
# ==========================================

def public_school_website(request):
    """Renders the official public-facing marketing homepage for Kabiero Academy"""
    return render(request, 'marketing/index.html')


def main_portal_home(request):
    """Calculates active analytical metrics summary numbers and renders the primary gateway page directly"""
    total_students = Student.objects.filter(is_active=True).count()
    total_collected = sum(r.amount for r in FeeReceipt.objects.filter(status='COMPLETED'))
    
    all_students = Student.objects.filter(is_active=True)
    defaulters_count = sum(1 for s in all_students if s.current_balance > 0)
            
    context = {
        'total_students': total_students,
        'total_collected': total_collected,
        'defaulters_count': defaulters_count,
    }
    return render(request, 'marketing/index.html', context)


# ==========================================
# 2. STUDENT OPERATIONAL WORKSPACE
# ==========================================

def student_registry_workstation(request):
    """The central cockpit to query, view, filter, and onboard learners cleanly"""
    streams = ClassStream.objects.all().order_by('name')
    
    search_query = request.GET.get('search_name', '').strip()
    stream_filter = request.GET.get('stream_id', '').strip()
    status_filter = request.GET.get('status_type', 'ACTIVE').strip()

    student_rows = Student.objects.all()

    if status_filter:
        student_rows = student_rows.filter(status=status_filter)
    if search_query:
        student_rows = student_rows.filter(
            models.Q(first_name__icontains=search_query) | 
            models.Q(last_name__icontains=search_query) |
            models.Q(admission_number__icontains=search_query)
        )
    if stream_filter:
        student_rows = student_rows.filter(class_stream_id=stream_filter)

    if request.method == 'POST' and 'onboard_student' in request.POST:
        try:
            Student.objects.create(
                admission_number=request.POST.get('admission_number').strip().upper(),
                first_name=request.POST.get('first_name').strip(),
                last_name=request.POST.get('last_name').strip(),
                gender=request.POST.get('gender'),
                class_stream_id=request.POST.get('class_stream'),
                guardian_name=request.POST.get('guardian_name').strip(),
                parent_phone=request.POST.get('parent_phone').strip(),
                blood_group=request.POST.get('blood_group'),
                known_allergies=request.POST.get('known_allergies', 'None Registered').strip()
            )
            messages.success(request, "Learner profile registered and allocated to class stream successfully!")
            return redirect('student_registry')
        except Exception as e:
            messages.error(request, f"Onboarding Failed: Ensure admission token unique. Error: {str(e)}")

    context = {
        'students': student_rows.order_by('-date_of_admission'),
        'streams': streams,
        'search_name': search_query,
        'selected_stream': int(stream_filter) if stream_filter else None,
        'selected_status': status_filter,
    }
    return render(request, 'finance/student_registry_workstation.html', context)


def single_student_profile_folder(request, student_id):
    """Compiles a deep file room overview of a student's full institutional records"""
    student = get_object_or_404(Student, id=student_id)
    discipline = student.discipline_logs.all().order_by('-date_reported')
    attendance = student.studentattendancerecord_set.all().order_by('-date')[:15] if hasattr(student, 'studentattendancerecord_set') else []

    if request.method == 'POST' and 'update_lifecycle' in request.POST:
        new_status = request.POST.get('status_lifecycle')
        student.status = new_status
        student.is_active = True if new_status == 'ACTIVE' else False
        student.save()
        messages.info(request, f"Student operational lifecycle adjusted to: {new_status}")
        return redirect('student_profile', student_id=student.id)

    if request.method == 'POST' and 'post_discipline' in request.POST:
        DisciplineReport.objects.create(
            student=student,
            infraction_details=request.POST.get('infraction_details'),
            severity=request.POST.get('severity'),
            action_taken=request.POST.get('action_taken')
        )
        messages.warning(request, "New disciplinary record logged onto student's file room matrix.")
        return redirect('student_profile', student_id=student.id)

    context = {
        'student': student,
        'discipline_logs': discipline,
        'attendance_logs': attendance
    }
    return render(request, 'finance/student_profile_folder.html', context)


# ==========================================
# 3. STAFF & HUMAN RESOURCES CONTROL DESK
# ==========================================

def staff_management_matrix(request):
    """Renders the comprehensive administrative employee workspace"""
    context = {
        'staff_roster': StaffProfile.objects.all().select_related('user'),
    }
    return render(request, 'finance/staff_management_matrix.html', context)


def faculty_directory(request):
    """Compiles and displays all active academic staff profiles and professional assignments"""
    teachers = Teacher.objects.all().order_by('last_name')
    return render(request, 'finance/faculty_directory.html', {'teachers': teachers})


# ==========================================
# 4. BURSAR FINANCIAL ENGINE
# ==========================================

@login_required
def bursar_dashboard(request):
    """Compiles the core accounting listing profiles directory ledger search engine"""
    search_query = request.GET.get('search', '').strip()
    
    if search_query:
        students = Student.objects.filter(
            is_active=True, first_name__icontains=search_query
        ) | Student.objects.filter(
            is_active=True, last_name__icontains=search_query
        ) | Student.objects.filter(
            is_active=True, admission_number__icontains=search_query
        )
    else:
        students = Student.objects.filter(is_active=True).order_by('admission_number')
        
    return render(request, 'finance/dashboard.html', {'students': students, 'search_query': search_query})


def student_account_statement(request, student_id):
    """Compiles an audit log trail statement sheet of every ledger payment invoice and receipt"""
    student = get_object_or_404(Student, id=student_id)
    invoices = student.fee_invoices.all().order_by('date_issued')
    receipts = student.fee_receipts.filter(status='COMPLETED').order_by('date_paid')
    
    context = {
        'student': student,
        'invoices': invoices,
        'receipts': receipts,
        'balance': student.current_balance
    }
    return render(request, 'finance/statement.html', context)


# finance/views.py
# Inside finance/views.py
from django.db.models import F # Add this at the top of your file if not already imported

# Inside finance/views.py
from decimal import Decimal
import datetime

def collect_fee_payment(request, student_id):
    """Processes system receipt vouchers and forces an explicit numerical write to the database field"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        channel = request.POST.get('payment_channel', 'MPESA').strip()
        raw_amount = request.POST.get('amount_paid', '0').strip()
        
        # 1. Automatic Serial Generation for Cash Allocations
        if channel == 'CASH':
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            ref_code = f"KAB-CSH-{timestamp}"
        else:
            ref_code = request.POST.get('reference_code', '').strip().upper()
            
        if not ref_code and channel != 'CASH':
            messages.error(request, "Mobile money or Bank transactions require a valid reference transaction code.")
            return render(request, 'finance/receipt_form.html', {'student': student})
            
        try:
            # Clean and convert the string input safely into a float/Decimal value
            clean_amount = Decimal(raw_amount) if raw_amount else Decimal('0')
            
            if clean_amount > 0:
                # 2. Log the Completed Receipt record into the database
                FeeReceipt.objects.create(
                    student=student,
                    reference_code=ref_code,
                    amount=clean_amount,
                    status='COMPLETED'
                )
                
                # 3. FORCE EXPLICIT MATHEMATICAL WRITE TO THE DATABASE COLUMN
                # Fetch fresh balance from DB, convert to Decimal, perform deduction
                current_db_balance = Decimal(str(student.current_balance))
                student.current_balance = current_db_balance - clean_amount
                student.save() # Writes directly to the row cell
                
                messages.success(request, f"Collection receipt voucher {ref_code} successfully posted for {student.first_name}. Balance adjusted to KES {student.current_balance:,.2f}")
                return redirect('bursar_dashboard')
            else:
                messages.error(request, "The collected transactional value amount must be greater than KES 0.")
                
        except Exception as e:
            messages.error(request, f"Financial processing transaction error: {str(e)}")
            
    return render(request, 'finance/receipt_form.html', {'student': student})
# ==========================================
# 5. ACADEMIC HUB & EVALUATION COCKPITS
# ==========================================

def academic_management_hub(request):
    """Serves as the master dashboard for lessons, timetables, and learning resources"""
    selected_stream_id = request.GET.get('stream_id')
    
    streams = ClassStream.objects.all()
    active_stream = ClassStream.objects.filter(id=selected_stream_id).first() if selected_stream_id else streams.first()
    
    timetable = TimetableSlot.objects.filter(stream=active_stream).select_related('subject', 'teacher__user') if active_stream else []
    lesson_plans = LessonPlan.objects.filter(stream=active_stream).select_related('subject', 'teacher__user') if active_stream else []
    
    context = {
        'streams': streams,
        'active_stream': active_stream,
        'timetable': timetable,
        'lesson_plans': lesson_plans,
        'learning_materials': LearningMaterial.objects.all().select_related('subject')[:8],
        'total_subjects': Subject.objects.count(),
    }
    return render(request, 'finance/academic_hub.html', context)


def generate_report_card_view(request, student_id):
    """Aggregates scores and compiles an on-the-fly printable Report Card sheet for a specific student"""
    student = get_object_or_404(Student, id=student_id)
    exam_records = ExamRecord.objects.filter(student=student, year=2026).select_related('subject')
    
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
        'today': timezone.now()
    }
    return render(request, 'finance/report_card_printout.html', context)


@login_required
def marks_entry_portal(request):
    """Renders a streamlined spreadsheet matrix for fast term marks collection"""
    subjects = Subject.objects.all().order_by('name')
    streams = ClassStream.objects.all().order_by('name')
    
    selected_subject_id = request.GET.get('subject')
    selected_stream_id = request.GET.get('stream')
    
    matrix_data = []
    
    if selected_subject_id and selected_stream_id:
        students = Student.objects.filter(class_stream_id=selected_stream_id, is_active=True).order_by('last_name')
        for student in students:
            record = ExamRecord.objects.filter(student=student, subject_id=selected_subject_id, year=2026).first()
            matrix_data.append({
                'student': student,
                'cat_1': record.cat_1 if record else '',
                'cat_2': record.cat_2 if record else '',
                'final_exam': record.final_exam if record else '',
                'total_marks': record.total_marks if record else None
            })

    context = {
        'subjects': subjects,
        'streams': streams,
        'matrix_data': matrix_data,
        'selected_subject': int(selected_subject_id) if selected_subject_id else None,
        'selected_stream': int(selected_stream_id) if selected_stream_id else None,
    }
    return render(request, 'finance/marks_entry_portal.html', context)


def academic_analytics_dashboard(request):
    """Aggregates exam fields across terms and monitors student performance trajectories"""
    selected_term = request.GET.get('term', 'TERM_2')
    
    all_streams = ClassStream.objects.all()
    stream_rankings = []
    for stream in all_streams:
        records = ExamRecord.objects.filter(student__class_stream=stream, term=selected_term, year=2026)
        total_records = records.count()
        avg_score = sum(r.total_marks for r in records) / total_records if total_records > 0 else 0.0
        stream_rankings.append({
            'name': stream.name, 
            'average': avg_score, 
            'count': Student.objects.filter(class_stream=stream, is_active=True).count()
        })
    stream_rankings.sort(key=lambda x: x['average'], reverse=True)

    all_subjects = Subject.objects.all()
    subject_performance = []
    for subject in all_subjects:
        records = ExamRecord.objects.filter(subject=subject, term=selected_term, year=2026)
        total_records = records.count()
        avg_score = sum(r.total_marks for r in records) / total_records if total_records > 0 else 0.0
        subject_performance.append({'name': subject.name, 'code': subject.code, 'average': avg_score})
    subject_performance.sort(key=lambda x: x['average'], reverse=True)

    all_students = Student.objects.filter(is_active=True)
    trajectory_list = []
    
    for s in all_students:
        t1_records = ExamRecord.objects.filter(student=s, term='TERM_1', year=2026)
        t2_records = ExamRecord.objects.filter(student=s, term='TERM_2', year=2026)
        
        t1_avg = sum(r.total_marks for r in t1_records) / t1_records.count() if t1_records.exists() else None
        t2_avg = sum(r.total_marks for r in t2_records) / t2_records.count() if t2_records.exists() else None
        
        if t1_avg is not None and t2_avg is not None:
            variance = t2_avg - t1_avg
            if variance <= -5.0: badge_class, icon, label = 'bg-danger', 'bi-graph-down-arrow', 'Slipping'
            elif variance >= 5.0: badge_class, icon, label = 'bg-success', 'bi-graph-up-arrow', 'Improving'
            else: badge_class, icon, label = 'bg-secondary', 'bi-arrow-right-short', 'Stable'
                
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
    return render(request, 'finance/analytics_dashboard.html', context)


# ==========================================
# 6. EXTERNAL PARENT INTERFACES
# ==========================================

# Inside finance/views.py (Section 6: External Parent Interfaces)

# Inside finance/views.py (Section 6: External Parent Interfaces)

def parent_portal_gateway(request):
    """Securely authenticates parents and streams live records directly into the tabbed dashboard panels"""
    if request.method == 'POST':
        phone_no = request.POST.get('parent_phone', '').strip()
        parent_id = request.POST.get('parent_id_number', '').strip()
        
        # Look up active records linked to this parent line
        matching_students = Student.objects.filter(parent_phone=phone_no, is_active=True)
        
        student = None
        for candidate in matching_students:
            if parent_id in candidate.guardian_name:
                student = candidate
                break
                
        if student is not None:
            # 1. LEDGER QUERIES
            invoices = student.fee_invoices.all().order_by('-date_issued')
            receipts = student.fee_receipts.filter(status='COMPLETED').order_by('-date_paid')
            
            # 2. FIXED ACADEMIC CORRECTION: Look up records explicitly matching this single student!
            exam_records = ExamRecord.objects.filter(student=student, year=2026).select_related('subject')
            
            # 3. FIXED ASSIGNMENTS CORRECTION: Look up assignments assigned to this student's specific class stream!
            homework_list = HomeworkAssignment.objects.filter(stream=student.class_stream).select_related('subject')
            
            # 4. FIXED BULLETIN BOARD CORRECTION: Fetch announcements meant for parents or the entire school body!
            announcements = SchoolAnnouncement.objects.filter(
                models.Q(target_audience='ALL_PARENTS') | models.Q(target_audience='ALL_STUDENTS')
            ).order_by('-date_published')[:5]
            
            # 5. SAFE ATTENDANCE LOOKUP LIST
            attendance_logs = student.attendance.all().order_by('-date')[:10] if hasattr(student, 'attendance') else []
            
            context = {
                'student': student, 
                'invoices': invoices, 
                'receipts': receipts,
                'exam_records': exam_records, 
                'attendance_logs': attendance_logs,
                'homework_list': homework_list,
                'announcements': announcements,
                'balance': student.current_balance
            }
            return render(request, 'finance/parent_dashboard.html', context)
        else:
            messages.error(request, "Access Denied: No active student account is verified with that Phone line and National ID pairing.")
            return redirect('parent_portal_gateway')
            
    return render(request, 'finance/parent_gateway_login.html')

# ==========================================
# 7. ROUTINE OPERATIONS & ASSET LOGISTICS
# ==========================================

def global_attendance_control_deck(request):
    """Calculates overall metrics charts and triggers localized absence warning sheets"""
    today = datetime.date.today()
    
    if request.method == 'POST' and 'toggle_attendance' in request.POST:
        record_id = request.POST.get('record_id')
        record_type = request.POST.get('type')
        new_status = request.POST.get('new_status')
        
        if record_type == 'STUDENT':
            rec = StudentAttendanceRecord.objects.get(id=record_id)
            rec.status = new_status
            rec.save()
            if new_status == 'ABSENT':
                messages.warning(request, f"🚨 SMS alert auto-staged for parent of {rec.student.first_name} ({rec.student.parent_phone})")
        elif record_type == 'TEACHER':
            rec = TeacherAttendanceRecord.objects.get(id=record_id)
            rec.status = new_status
            rec.save()
        return redirect('attendance_deck')

    students = Student.objects.filter(is_active=True)
    staff_members = StaffProfile.objects.all()
    
    for s in students:
        StudentAttendanceRecord.objects.get_or_create(student=s, date=today, defaults={'status': 'PRESENT'})
    for st in staff_members:
        TeacherAttendanceRecord.objects.get_or_create(staff=st, date=today, defaults={'status': 'PRESENT', 'time_in': datetime.time(7, 45)})

    context = {
        'today': today,
        'student_attendance': StudentAttendanceRecord.objects.filter(date=today).select_related('student__class_stream'),
        'teacher_attendance': TeacherAttendanceRecord.objects.filter(date=today).select_related('staff__user'),
        'total_present_students': StudentAttendanceRecord.objects.filter(date=today, status='PRESENT').count(),
        'total_absent_students': StudentAttendanceRecord.objects.filter(date=today, status='ABSENT').count(),
        'total_present_teachers': TeacherAttendanceRecord.objects.filter(date=today, status='PRESENT').count(),
    }
    return render(request, 'finance/attendance_control_deck.html', context)


def inventory_asset_control_deck(request):
    """Monitors school property stores, balances quantities, and audits maintenance reports"""
    if request.method == 'POST' and 'log_repair' in request.POST:
        asset_id = request.POST.get('asset_id')
        issue = request.POST.get('issue_reported')
        cost = request.POST.get('cost_kes', 0.00) or 0.00
        
        asset_obj = SchoolAsset.objects.get(id=asset_id)
        asset_obj.status = 'UNDER_REPAIR'
        asset_obj.save()
        
        AssetMaintenanceLog.objects.create(asset=asset_obj, issue_reported=issue, cost_incurred_kes=cost, is_resolved=False)
        messages.warning(request, f"🔧 Asset status updated: {asset_obj.name} placed under maintenance logs.")
        return redirect('inventory_deck')

    selected_category = request.GET.get('category', 'ALL')
    assets = SchoolAsset.objects.all().order_by('category', 'name') if selected_category == 'ALL' else SchoolAsset.objects.filter(category=selected_category).order_by('name')

    context = {
        'assets': assets,
        'selected_category': selected_category,
        'maintenance_tickets': AssetMaintenanceLog.objects.filter(is_resolved=False).select_related('asset'),
        'total_operational': SchoolAsset.objects.filter(status='OPERATIONAL').count(),
        'total_repair_flags': SchoolAsset.objects.filter(status='UNDER_REPAIR').count(),
    }
    return render(request, 'finance/inventory_control_deck.html', context)


def executive_analytics_kpi_dashboard(request):
    """Compiles real-time institutional KPIs, fee performance ratios, and academic analytics charts"""
    total_learners = Student.objects.filter(is_active=True).count()
    total_instructors = StaffProfile.objects.filter(role_designation='TEACHER', current_status='ACTIVE').count()
    
    total_invoiced = FeeInvoice.objects.aggregate(total=Sum('amount'))['total'] or 0.00
    total_collected = FeeReceipt.objects.filter(status='COMPLETED').aggregate(total=Sum('amount'))['total'] or 0.00
    total_outstanding_arrears = Student.objects.filter(is_active=True).aggregate(total=Sum('current_balance'))['total'] or 0.00
    
    collection_efficiency = (float(total_collected) / float(total_invoiced) * 100) if total_invoiced > 0 else 0.0
    
    total_assets = SchoolAsset.objects.aggregate(total=Sum('total_quantity'))['total'] or 0
    assets_in_workshop = SchoolAsset.objects.filter(status='UNDER_REPAIR').count()
    facility_operational_rate = ((total_assets - assets_in_workshop) / total_assets * 100) if total_assets > 0 else 100.0

    security_logs = [
        {"timestamp": "Just now", "user": "kamau_p (Accountant)", "action": "Generated Fee Invoice #INV-2026-088", "status": "SUCCESS", "icon": "bi-receipt"},
        {"timestamp": "12 mins ago", "user": "mwangi_j (Teacher)", "action": "Uploaded Learning Material: 'Simultaneous Equations Kit'", "status": "SUCCESS", "icon": "bi-cloud-upload"},
        {"timestamp": "1 hr ago", "user": "amina_o (Principal)", "action": "Approved Weekly Lesson Plan for Form 1 Alpha", "status": "SUCCESS", "icon": "bi-check-circle"},
        {"timestamp": "2 hrs ago", "user": "System Gateway", "action": "Staged Parent SMS Alert: Student Admission KAB/2026/002 Absent", "status": "ALERT", "icon": "bi-envelope-exclamation"},
    ]

    context = {
        'total_students': total_learners,
        'total_teachers': total_instructors,
        'total_invoiced': total_invoiced,
        'total_collected': total_collected,
        'total_arrears': total_outstanding_arrears,
        'collection_efficiency': round(collection_efficiency, 1),
        'operational_rate': round(facility_operational_rate, 1),
        'assets_at_risk': assets_in_workshop,
        'security_logs': security_logs,
    }
    return render(request, 'finance/executive_reporting.html', context)


# ==========================================
# 8. SECURITY & ACCESS CONTROL CHANNELS
# ==========================================

def staff_login_view(request):
    """Enforces role-based redirection, ensuring even Superuser logins honor the clicked dashboard gateway"""
    target_role = request.GET.get('role', 'Admin').strip()
    
    # Session clearing safeguard block
    if request.user.is_authenticated and request.method == 'GET':
        logout(request)

    if request.method == 'POST':
        username_input = request.POST.get('username', '').strip()
        password_input = request.POST.get('password', '')
        user = authenticate(request, username=username_input, password=password_input)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Access Authorized. Environment context: {target_role}")
            
            # 🚀 THE FIX: Save the chosen role in session storage. 
            # This completely overrides default superuser structural fallback rules inside base.html!
            request.session['active_role_context'] = target_role
            
            if target_role == 'Bursar':
                return redirect('bursar_dashboard')
            elif target_role in ['Admin', 'Headteacher', 'Deputy']:
                return redirect('executive_kpis')
            elif target_role == 'Teacher':
                return redirect('academic_hub')
            elif target_role == 'Support':
                return redirect('inventory_deck')
            
            return redirect('public_home')
        else:
            messages.error(request, f"Authentication failed for {target_role} credentials workspace. Access Denied.")
            return redirect(f"{request.path}?role={target_role}")
            
    return render(request, 'finance/staff_login.html', {'target_role': target_role})


def staff_logout_view(request):
    """Terminates active staff session tokens and securely clear states"""
    logout(request)
    messages.info(request, "Logged out successfully. Have a wonderful day!")
    return redirect('public_home')


def developer_debug_console_hub(request):
    """Provides a master dashboard revealing raw database states and rapid injection tools"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        action = request.POST.get('action')
        
        if action == 'inject_mock_data':
            alpha, _ = ClassStream.objects.get_or_create(name="Form 1 Alpha", defaults={"room_number": "Room 101", "capacity": 45})
            beta, _ = ClassStream.objects.get_or_create(name="Form 2 Beta", defaults={"room_number": "Room 102", "capacity": 40})
            
           # Locate inside the developer_debug_console_hub inside finance/views.py:
            mock_students = [
    {"adm": "KAB/2026/001", "f": "Ezra", "l": "Kipchirchir", "g": "M", "b": "O+", "stream": alpha, "parent": "David Kipchirchir (ID: 87654321)", "phone": "0711223344"},
    # 🚀 UPDATED: Appended a mock ID number directly to the parent field for effortless demo verification
    {"adm": "KAB/2026/002", "f": "Mercy", "l": "Wambui", "g": "F", "b": "A+", "stream": alpha, "parent": "Grace Wambui (ID: 24681012)", "phone": "0722334455"},
    {"adm": "KAB/2026/003", "f": "Abdi", "l": "Idris", "g": "M", "b": "B+", "stream": beta, "parent": "Idris Farah (ID: 13579111)", "phone": "0733445566"},
            ]
            for s in mock_students:
                obj, created = Student.objects.get_or_create(
                    admission_number=s["adm"],
                    defaults={
                        "first_name": s["f"], "last_name": s["l"], "gender": s["g"], "blood_group": s["b"], "class_stream": s["stream"],
                        "guardian_name": s["parent"], "parent_phone": s["phone"], "known_allergies": "None", "current_balance": 35000.00
                    }
                )
                if created:
                    DisciplineReport.objects.create(student=obj, infraction_details="Arrived late for morning preps", severity="MINOR", action_taken="Verbal warning logged")
            
            staff_data = [
                {"username": "mwangi_j", "first": "John", "last": "Mwangi", "num": "EMP/2026/101", "role": "TEACHER", "sal": 55000.00, "spec": "Chemistry / Biology"},
                {"username": "amina_o", "first": "Amina", "last": "O Omar", "num": "EMP/2026/102", "role": "PRINCIPAL", "sal": 95000.00, "spec": "Administration"},
                {"username": "kamau_p", "first": "Peter", "last": "Kamau", "num": "EMP/2026/103", "role": "ACCOUNTANT", "sal": 60000.00, "spec": "Finance / Accounts"},
            ]
            for s in staff_data:
                u, created = User.objects.get_or_create(username=s["username"], defaults={"first_name": s["first"], "last_name": s["last"]})
                if created:
                    u.set_password("sms_pass2026")
                    u.save()
                    StaffProfile.objects.get_or_create(user=u, employee_number=s["num"], defaults={"role_designation": s["role"], "base_salary_kes": s["sal"], "specialization": s["spec"], "current_status": "ACTIVE"})

            maths_sub, _ = Subject.objects.get_or_create(name="Mathematics", defaults={"code": "MAT101"})
            HomeworkAssignment.objects.get_or_create(stream=alpha, subject=maths_sub, title="Algebraic Expressions Review", defaults={"task_instructions": "Complete exercises 4B and 4C on page 92.", "submission_deadline": datetime.date.today() + datetime.timedelta(days=3)})
            SchoolAnnouncement.objects.get_or_create(title="Upcoming Annual General Meeting (AGM)", defaults={"announcement_body": "Term 2 AGM is scheduled for next Friday at 10:00 AM.", "target_audience": "ALL_PARENTS"})

            SchoolAsset.objects.get_or_create(serial_or_isbn="9780198425113", defaults={"name": "Oxford KLB Mathematics Form 1", "category": "TEXTBOOKS", "total_quantity": 120, "available_quantity": 115, "assigned_location": "Cabinet B", "status": "OPERATIONAL"})
            SchoolAsset.objects.get_or_create(serial_or_isbn="KAB-COMP-LAB-04", defaults={"name": "HP ProDesk Desktop Intel i5", "category": "LAB_EQUIP", "total_quantity": 25, "available_quantity": 24, "assigned_location": "Computer Lab", "status": "OPERATIONAL"})
            SchoolAsset.objects.get_or_create(serial_or_isbn="KAB-FUR-DSK-88", defaults={"name": "Double Seater Wooden Desks", "category": "FURNITURE", "total_quantity": 60, "available_quantity": 60, "assigned_location": "Form 1 Alpha", "status": "OPERATIONAL"})

            teacher_profile = StaffProfile.objects.filter(role_designation='TEACHER').first()
            if teacher_profile:
                LessonPlan.objects.get_or_create(teacher=teacher_profile, subject=maths_sub, stream=alpha, topic="Linear Inequalities", defaults={"objectives": "Solve simple linear inequalities.", "week_number": 4, "date_planned": datetime.date.today(), "is_approved": True})
                TimetableSlot.objects.get_or_create(stream=alpha, subject=maths_sub, teacher=teacher_profile, day="MON", defaults={"time_start": "08:20:00", "time_end": "09:00:00"})
                TimetableSlot.objects.get_or_create(stream=alpha, subject=maths_sub, teacher=teacher_profile, day="WED", defaults={"time_start": "10:40:00", "time_end": "11:20:00"})

            LearningMaterial.objects.get_or_create(subject=maths_sub, title="Form 1 Revision Kit", defaults={"material_type": "NOTES", "resource_url": "https://drive.google.com/file/d/sample"})
            return JsonResponse({"status": "success", "message": "Injected data successfully!"})
            
        if action == 'purge_all_data':
            for model in [DisciplineReport, Student, ClassStream, FeeInvoice, FeeReceipt, StaffProfile, HomeworkAssignment, SchoolAnnouncement, SchoolAsset, AssetMaintenanceLog, LessonPlan, LearningMaterial, TimetableSlot]:
                model.objects.all().delete()
            return JsonResponse({"status": "success", "message": "Database cleared successfully!"})

    context = {
        'total_students': Student.objects.count(),
        'total_streams': ClassStream.objects.count(),
        'total_infractions': DisciplineReport.objects.count(),
        'total_staff': StaffProfile.objects.count(),
        'raw_students': Student.objects.all().select_related('class_stream')[:10],
        'raw_staff': StaffProfile.objects.all().select_related('user'),
    }
    return render(request, 'finance/developer_debug_console.html', context)
# Place this inside finance/views.py

def teacher_sms_broadcast(request):
    """TEACHER ENGINE: Supports BOTH bulk class stream broadcasts and targeted single student parent alerts"""
    if request.session.get('active_role_context') not in ['Teacher', 'Teachers', 'Headteacher', 'Deputy', 'Admin', 'Bursar']:
        messages.error(request, "Access Denied: Text broadcasting components are restricted to authorized personnel.")
        return redirect('public_home')
        
    streams = ClassStream.objects.all().order_by('name')
    target_student_id = request.GET.get('student_id')
    selected_stream_id = request.GET.get('stream_id')
    
    single_student = None
    active_stream = None
    recipients_count = 0
    
    if target_student_id:
        single_student = get_object_or_404(Student, id=target_student_id)
    elif selected_stream_id:
        active_stream = ClassStream.objects.filter(id=selected_stream_id).first()
        if active_stream:
            recipients_count = Student.objects.filter(class_stream=active_stream, is_active=True).count()

    if request.method == 'POST':
        sms_text = request.POST.get('broadcast_message', '').strip()
        mode = request.POST.get('broadcast_mode', 'BULK')
        
        if mode == 'SINGLE':
            student_id = request.POST.get('target_student_id')
            student_obj = Student.objects.get(id=student_id)
            
            SchoolAnnouncement.objects.create(
                title=f"Individual Update: {student_obj.first_name}",
                announcement_body=sms_text,
                target_audience='ALL_PARENTS'
            )
            messages.success(request, f"⚡ Direct SMS alert transmitted to {student_obj.guardian_name} for {student_obj.first_name}.")
        else:
            stream_id = request.POST.get('target_stream')
            stream_obj = ClassStream.objects.get(id=stream_id)
            parent_phones = Student.objects.filter(class_stream=stream_obj, is_active=True).values_list('parent_phone', flat=True)
            
            SchoolAnnouncement.objects.create(
                title=f"Class Bulletin: {stream_obj.name}",
                announcement_body=sms_text,
                target_audience='ALL_PARENTS'
            )
            messages.success(request, f"📢 Broadcast Dispatched to {len(parent_phones)} parent lines for {stream_obj.name}.")
            
        return redirect('academic_hub')

    context = {
        'streams': streams,
        'active_stream': active_stream,
        'recipients_count': recipients_count,
        'single_student': single_student,
    }
    return render(request, 'finance/teacher_sms.html', context)

    # Inside finance/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
import datetime

def fee_defaulters_sms_portal(request):
    """BURSAR ENGINE: Pulls outstanding balances and simulates bulk arrears notifications"""
    if request.session.get('active_role_context') not in ['Bursar', 'Headteacher', 'Admin', 'Teachers', 'Teacher']:
        messages.error(request, "Access Denied: The SMS Treasury Router is restricted to authorized staff.")
        return redirect('public_home')
        
    all_students = Student.objects.filter(is_active=True)
    defaulters_queue = []
    
    for student in all_students:
        balance = student.current_balance
        if balance > 0:
            defaulters_queue.append({
                'student': student,
                'balance': balance,
                'message_preview': f"Dear Parent, please note Kabiero Academy records show an outstanding balance of KES {balance:,.2f} for Adm {student.admission_number}."
            })
            
    if request.method == 'POST':
        count = len(defaulters_queue)
        messages.success(request, f"🚀 Bulk Financial Dispatch Success: {count} arrears reminders successfully transmitted.")
        return redirect('bursar_dashboard')
        
    return render(request, 'finance/sms_portal.html', {'defaulters': defaulters_queue})


    import os
import csv
import datetime
from django.shortcuts import render, redirect
from django.conf import settings

# A helper class that formats the CSV rows so your HTML templates can read them
class LiveCSVStudent:
    def __init__(self, row):
        self.admission_number = row[0].strip()
        
        # Safe ID mapping so your view statement links don't crash
        try:
            self.id = int(self.admission_number)
        except ValueError:
            self.id = 999

        # Splits full name into first and last name for the initials circles
        full_name = row[1].strip()
        name_parts = full_name.split(" ", 1)
        self.first_name = name_parts[0]
        self.last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        self.gender = row[2].strip()
        self.current_grade = row[5].strip() if (len(row) > 5 and row[5].strip()) else "Grade 1"
        
        # Tricks the template into reading student.class_stream.name smoothly
        class StreamWrapper:
            def __init__(self, grade_str):
                self.name = grade_str
        self.class_stream = StreamWrapper(self.current_grade)
        
        # Parent information defaults for the demo
        self.guardian_name = row[8].strip() if (len(row) > 8 and row[8].strip()) else "Not Provided"
        self.parent_phone = row[9].strip() if (len(row) > 9 and row[9].strip()) else "Contact Office"
        self.guardian_relation = "Primary Contact"
        
        self.blood_group = "Unset"
        self.current_balance = 0.00


def _load_students_from_csv():
    """Helper function to load the CSV file safely regardless of directory depth"""
    csv_path = os.path.join(settings.BASE_DIR, '..', 'Crescent Heights School - STUDENTS.csv')
    if not os.path.exists(csv_path):
        csv_path = os.path.join(settings.BASE_DIR, 'Crescent Heights School - STUDENTS.csv')
        
    students_list = []
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            for row in reader:
                if len(row) >= 2 and row[1].strip():
                    students_list.append(LiveCSVStudent(row))
    return students_list


# ── FUNCTION A: FOR YOUR MASTER STUDENT REGISTRY TABLE ──
def student_registry_workstation(request):
    students = _load_students_from_csv()
    students.sort(key=lambda s: s.first_name)
    context = {'students': students}
    return render(request, 'finance/student_registry_workstation.html', context)


# ── FUNCTION B: FOR YOUR ATTENDANCE DESK DROPDOWN GRID ──
def mark_daily_attendance_registry(request):
    students_pool = _load_students_from_csv()
    
    # Clean primary school levels matching Crescent Heights exactly
    grade_order = ["Playgroup", "PP1", "PP2", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6"]
    
    class MockDropdownStream:
        def __init__(self, name_string):
            self.id = name_string
            self.name = name_string
            
    streams = [MockDropdownStream(g) for g in grade_order]
    
    selected_stream = request.GET.get('stream_id', '').strip()
    target_date_str = request.GET.get('date', '').strip()
    
    if not target_date_str:
        target_date = datetime.date.today().strftime('%Y-%m-%d')
    else:
        target_date = target_date_str
        
    # Filter down to the selected grade live
    students = [s for s in students_pool if s.current_grade == selected_stream]
    students.sort(key=lambda s: s.first_name)
    
    existing_records = {s.id: "PRESENT" for s in students}
        
    if request.method == 'POST':
        return redirect(f"{request.path}?stream_id={selected_stream}&date={target_date}")
        
    context = {
        'streams': streams,
        'selected_stream': selected_stream,
        'target_date': target_date,
        'students': students,
        'existing_records': existing_records,
    }
    return render(request, 'finance/attendance_registry.html', context)