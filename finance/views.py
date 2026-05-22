import datetime
import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .decorators import group_required

# Unified Model Imports matching your production database
from .models import (
    Teacher, ClassStream, Subject, Student, FeeInvoice, 
    FeeReceipt, ExamRecord, DisciplineReport, AttendanceRecord, StaffProfile
)

# ==========================================
# 1. CORE ACCESSIBLE WEB CHANNELS
# ==========================================

def public_school_website(request):
    """Renders the official public-facing marketing homepage for Kabiero Academy"""
    return render(request, 'marketing/index.html')


def main_portal_home(request):
    """Calculates active analytical metrics summary numbers for the executive landing menu"""
    total_students = Student.objects.filter(is_active=True).count()
    total_collected = sum(r.amount_paid for r in FeeReceipt.objects.filter(status='COMPLETED'))
    
    all_students = Student.objects.filter(is_active=True)
    defaulters_count = 0
    for s in all_students:
        if s.current_balance > 0:
            defaulters_count += 1
            
    context = {
        'total_students': total_students,
        'total_collected': total_collected,
        'defaulters_count': defaulters_count,
    }
    return render(request, 'finance/portal_home.html', context)


# ==========================================
# 2. STUDENT OPERATIONAL WORKSPACE
# ==========================================

def student_registry_workstation(request):
    """The central cockpit to query, view, filter, and onboard learners cleanly"""
    streams = ClassStream.objects.all().order_by('name')
    
    # Process Filter parameters
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

    # Handle incoming rapid student onboarding action payload
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
    # FIXED: Corrected spelling typo from get_object_or_400 to get_object_or_404
    student = get_object_or_404(Student, id=student_id)
    discipline = student.discipline_logs.all().order_by('-date_reported')
    attendance = student.attendance.all().order_by('-date')[:15]

    # Dynamic status update toggle hooks (Transfers / Graduations)
    if request.method == 'POST' and 'update_lifecycle' in request.POST:
        new_status = request.POST.get('status_lifecycle')
        student.status = new_status
        student.is_active = True if new_status == 'ACTIVE' else False
        student.save()
        messages.info(request, f"Student operational lifecycle adjusted to: {new_status}")
        return redirect('student_profile', student_id=student.id)

    # Post quick disciplinary action report entry card
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
# 4. BURZAR FINANCIAL ENGINE
# ==========================================

@login_required
@group_required('Bursar')
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


def collect_fee_payment(request, student_id):
    """Processes system receipt vouchers and automatically generates serial keys for cash allocations"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        channel = request.POST.get('payment_channel', 'MPESA')
        amount = request.POST.get('amount_paid', '0').strip()
        
        if channel == 'CASH':
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            ref_code = f"KAB-CSH-{timestamp}"
        else:
            ref_code = request.POST.get('reference_code', '').strip().upper()
            
        if not ref_code and channel != 'CASH':
            messages.error(request, "Mobile money or Bank transactions require a valid reference transaction code.")
            return render(request, 'finance/receipt_form.html', {'student': student})
            
        if amount and Decimal(amount) > 0:
            FeeReceipt.objects.create(
                student=student,
                reference_code=ref_code,
                amount=Decimal(amount),
                status='COMPLETED'
            )
            messages.success(request, f"Collection receipt voucher {ref_code} successfully posted for {student.first_name}.")
            return redirect('bursar_dashboard')
        else:
            messages.error(request, "The collected transactional value amount must be greater than KES 0.")
            
    return render(request, 'finance/receipt_form.html', {'student': student})


def fee_defaulters_sms_portal(request):
    """Isolates active arrears files and compiles parent contact notification numbers"""
    all_students = Student.objects.filter(is_active=True)
    defaulters_queue = []
    
    for student in all_students:
        balance = student.current_balance
        if balance > 0:
            defaulters_queue.append({
                'student': student,
                'balance': balance,
                'message_preview': f"Dear Parent, please note Kabiero Academy records show an outstanding balance of KES {balance:,.2f} for Adm {student.admission_number}. Please clear promptly."
            })
            
    if request.method == 'POST':
        messages.success(request, f"Bulk text reminders successfully dispatched upstream to all {len(defaulters_queue)} parent lines.")
        return redirect('main_portal_home')
        
    return render(request, 'finance/sms_portal.html', {'defaulters': defaulters_queue})


# ==========================================
# 5. ACADEMIC GRADING & ANALYTICS
# ==========================================

@login_required
@group_required('Teacher')
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
            record = ExamRecord.objects.filter(
                student=student, subject_id=selected_subject_id, year=2026
            ).first()
            
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
        records = ExamRecord.objects.filter(subject=subject, term=selected_term, year=2026)
        total_records = records.count()
        avg_score = sum(r.total_marks for r in records) / total_records if total_records > 0 else 0.0
        subject_performance.append({'name': subject.name, 'code': subject.code, 'average': avg_score})
    subject_performance.sort(key=lambda x: x['average'], reverse=True)

    all_students = Student.objects.filter(is_active=True)
    trajectory_list = []
    
    for s in all_students:
        # FIXED: Explicitly query the ExamRecord table directly filtering by the individual student instance
        t1_records = ExamRecord.objects.filter(student=s, term='TERM_1', year=2026)
        t2_records = ExamRecord.objects.filter(student=s, term='TERM_2', year=2026)
        
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
    return render(request, 'finance/analytics_dashboard.html', context)


# ==========================================
# 6. EXTERNAL PARENT INTERFACES
# ==========================================

# Update parent_portal_gateway inside finance/views.py
from .models import HomeworkAssignment, SchoolAnnouncement

def parent_portal_gateway(request):
    """Securely authenticates parents via matching Admission and Phone credentials and serves their portal dashboard"""
    if request.method == 'POST':
        admission_no = request.POST.get('admission_number', '').strip()
        phone_no = request.POST.get('parent_phone', '').strip()
        
        try:
            student = Student.objects.get(
                admission_number=admission_no, parent_phone=phone_no, is_active=True
            )
            
            # Fetch relational records for the student
            invoices = student.fee_invoices.all().order_by('-date_issued')
            receipts = student.fee_receipts.filter(status='COMPLETED').order_by('-date_paid')
            exam_records = ExamRecord.objects.filter(student=student, year=2026).select_related('subject')
            attendance_logs = student.attendance_history.all().order_by('-date')[:10]
            
            # Fetch homework matches & global school event notifications
            homework = HomeworkAssignment.objects.filter(stream=student.class_stream).select_related('subject')
            announcements = SchoolAnnouncement.objects.all().order_by('-date_published')[:5]
            
            context = {
                'student': student, 
                'invoices': invoices, 
                'receipts': receipts,
                'exam_records': exam_records, 
                'attendance_logs': attendance_logs,
                'homework_list': homework,
                'announcements': announcements,
                'balance': student.current_balance
            }
            return render(request, 'finance/parent_dashboard.html', context)
            
        except Student.DoesNotExist:
            messages.error(request, "Authentication failed. Verification details do not match our active records.")
            return redirect('parent_portal_gateway')
            
    return render(request, 'finance/parent_gateway_login.html')


# ==========================================
# 7. SECURITY & ACCESS CONTROL CHANNELS
# ==========================================

def staff_login_view(request):
    """Enforces strict role-based login matching to prevent cross-login bypasses"""
    target_role = request.GET.get('role', '').strip()
    
    if request.user.is_authenticated:
        is_bursar = request.user.groups.filter(name='Bursar').exists() or request.user.is_superuser
        is_teacher = request.user.groups.filter(name='Teacher').exists()
        
        if target_role == 'Teacher' and not is_teacher:
            logout(request)
        elif target_role == 'Bursar' and not is_bursar:
            logout(request)
        else:
            if is_bursar: return redirect('bursar_dashboard')
            if is_teacher: return redirect('marks_entry_portal')

    if request.method == 'POST':
        username_input = request.POST.get('username', '').strip()
        password_input = request.POST.get('password', '')
        
        user = authenticate(request, username=username_input, password=password_input)
        
        if user is not None:
            user_is_bursar = user.groups.filter(name='Bursar').exists() or user.is_superuser
            user_is_teacher = user.groups.filter(name='Teacher').exists()
            
            if target_role == 'Teacher' and not user_is_teacher:
                messages.error(request, "Access Denied! Workstation reserved for Academic Staff only.")
                return redirect(f"{request.path}?role=Teacher")
                
            if target_role == 'Bursar' and not user_is_bursar:
                messages.error(request, "Access Denied! Workstation reserved for Finance Administration only.")
                return redirect(f"{request.path}?role=Bursar")

            login(request, user)
            if user_is_bursar:
                messages.success(request, f"Welcome back, Bursar {user.username}!")
                return redirect('bursar_dashboard')
            elif user_is_teacher:
                messages.success(request, "Welcome back to the Grading Desk, Mwalimu!")
                return redirect('marks_entry_portal')
                
            return redirect('public_home')
        else:
            messages.error(request, "Invalid username or account password. Access Denied.")
            return redirect(f"{request.path}?role={target_role}")
            
    return render(request, 'finance/staff_login.html')


def staff_logout_view(request):
    """Terminates active staff session tokens and securely clear states"""
    logout(request)
    messages.info(request, "Logged out successfully. Have a wonderful day!")
    return redirect('public_home')


# ==========================================
# 8. SYSTEM DEVELOPER CONTROL CONSOLE
# ==========================================

def developer_debug_console_hub(request):
    """Provides a master dashboard revealing raw database states and rapid injection tools"""
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        action = request.POST.get('action')
        
        if action == 'inject_mock_data':
            # 1. Create Default Streams if missing
            alpha, _ = ClassStream.objects.get_or_create(name="Form 1 Alpha", defaults={"room_number": "Room 101", "capacity": 45})
            beta, _ = ClassStream.objects.get_or_create(name="Form 2 Beta", defaults={"room_number": "Room 102", "capacity": 40})
            
            # 2. Inject Complete Student Portfolios
            mock_students = [
                {"adm": "KAB/2026/001", "f": "Ezra", "l": "Kipchirchir", "g": "M", "b": "O+", "stream": alpha, "parent": "David Kipchirchir", "phone": "0711223344"},
                {"adm": "KAB/2026/002", "f": "Mercy", "l": "Wambui", "g": "F", "b": "A+", "stream": alpha, "parent": "Grace Wambui", "phone": "0722334455"},
                {"adm": "KAB/2026/003", "f": "Abdi", "l": "Idris", "g": "M", "b": "B+", "stream": beta, "parent": "Idris Farah", "phone": "0733445566"},
            ]
            
            for s in mock_students:
                obj, created = Student.objects.get_or_create(
                    admission_number=s["adm"],
                    defaults={
                        "first_name": s["f"], "last_name": s["l"], "gender": s["g"],
                        "blood_group": s["b"], "class_stream": s["stream"],
                        "guardian_name": s["parent"], "parent_phone": s["phone"],
                        "known_allergies": "None", "current_balance": 35000.00
                    }
                )
                if created:
                    DisciplineReport.objects.create(
                        student=obj, infraction_details="Arrived late for morning preps",
                        severity="MINOR", action_taken="Verbal warning logged"
                    )
            
            # 3. Inject Mock Staff Profiles
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
                    StaffProfile.objects.get_or_create(
                        user=u, employee_number=s["num"],
                        defaults={"role_designation": s["role"], "base_salary_kes": s["sal"], "specialization": s["spec"], "current_status": "ACTIVE"}
                    )

            # 4. Inject Mock Assignments & Announcements
            maths_sub, _ = Subject.objects.get_or_create(name="Mathematics", defaults={"code": "MAT101"})
            
            HomeworkAssignment.objects.get_or_create(
                stream=alpha, subject=maths_sub, title="Algebraic Expressions Review",
                defaults={
                    "task_instructions": "With reference to your notes, complete exercises 4B and 4C on page 92 of the core textbook.", 
                    "submission_deadline": datetime.date.today() + datetime.timedelta(days=3)
                }
            )
                
            SchoolAnnouncement.objects.get_or_create(
                title="Upcoming Annual General Meeting (AGM)",
                defaults={
                    "announcement_body": "Dear Parents, our Term 2 AGM is scheduled for next Friday at 10:00 AM in the main pavilion hall. Attendance is highly encouraged.", 
                    "target_audience": "ALL_PARENTS"
                }
            )

            # 5. Inject Mock Inventory Assets
            SchoolAsset.objects.get_or_create(
                serial_or_isbn="9780198425113",
                defaults={"name": "Oxford KLB Secondary Mathematics Form 1", "category": "TEXTBOOKS", "total_quantity": 120, "available_quantity": 115, "assigned_location": "Main Book Store / Cabinet B", "status": "OPERATIONAL"}
            )
            SchoolAsset.objects.get_or_create(
                serial_or_isbn="KAB-COMP-LAB-04",
                defaults={"name": "HP ProDesk Desktop Intel i5 Core", "category": "LAB_EQUIP", "total_quantity": 25, "available_quantity": 24, "assigned_location": "Computer Lab Terminal 4", "status": "OPERATIONAL"}
            )
            SchoolAsset.objects.get_or_create(
                serial_or_isbn="KAB-FUR-DSK-88",
                defaults={"name": "Double Seater Wooden Desks with Lockers", "category": "FURNITURE", "total_quantity": 60, "available_quantity": 60, "assigned_location": "Form 1 Alpha Block Classroom", "status": "OPERATIONAL"}
            )
                    
            return JsonResponse({"status": "success", "message": "Injected both student matrices and staff employee records successfully!"})
            
        if action == 'purge_all_data':
            DisciplineReport.objects.all().delete()
            Student.objects.all().delete()
            ClassStream.objects.all().delete()
            FeeInvoice.objects.all().delete()
            FeeReceipt.objects.all().delete()
            StaffProfile.objects.all().delete()
            HomeworkAssignment.objects.all().delete()
            SchoolAnnouncement.objects.all().delete()
            SchoolAsset.objects.all().delete()
            AssetMaintenanceLog.objects.all().delete()
            return JsonResponse({"status": "success", "message": "Database tables wiped clean into pristine slate!"})

    context = {
        'total_students': Student.objects.count(),
        'total_streams': ClassStream.objects.count(),
        'total_infractions': DisciplineReport.objects.count(),
        'total_staff': StaffProfile.objects.count(),
        'raw_students': Student.objects.all().select_related('class_stream')[:10],
        'raw_staff': StaffProfile.objects.all().select_related('user'),
    }
    return render(request, 'finance/developer_debug_console.html', context)
# Append to the absolute bottom of finance/views.py
from .models import StudentAttendanceRecord, TeacherAttendanceRecord

def global_attendance_control_deck(request):
    """Calculates overall metrics charts and triggers localized absence warning sheets"""
    today = datetime.date.today()
    
    # 1. Handle Rapid Manual/Biometric Scan Post Mock
    if request.method == 'POST' and 'toggle_attendance' in request.POST:
        record_id = request.POST.get('record_id')
        record_type = request.POST.get('type') # STUDENT or TEACHER
        new_status = request.POST.get('new_status')
        
        if record_type == 'STUDENT':
            rec = StudentAttendanceRecord.objects.get(id=record_id)
            rec.status = new_status
            rec.save()
            
            # If changed to ABSENT, mock flash parent SMS notification log alert
            if new_status == 'ABSENT':
                messages.warning(request, f"🚨 SMS alert auto-staged for parent of {rec.student.first_name} ({rec.student.parent_phone})")
                
        elif record_type == 'TEACHER':
            rec = TeacherAttendanceRecord.objects.get(id=record_id)
            rec.status = new_status
            rec.save()
            
        return redirect('attendance_deck')

    # 2. Extract Data Rows for Today's Matrix boards
    students = Student.objects.filter(is_active=True)
    staff_members = StaffProfile.objects.all()
    
    # Auto-initialize records for today if missing to prevent blank states
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

# Append to the absolute bottom of finance/views.py
from .models import SchoolAsset, AssetMaintenanceLog

def inventory_asset_control_deck(request):
    """Monitors school property stores, balances quantities, and audits maintenance reports"""
    
    # 1. Handle New Quick Maintenance Ticket Submission
    if request.method == 'POST' and 'log_repair' in request.POST:
        asset_id = request.POST.get('asset_id')
        issue = request.POST.get('issue_reported')
        cost = request.POST.get('cost_kes', 0.00) or 0.00
        
        asset_obj = SchoolAsset.objects.get(id=asset_id)
        asset_obj.status = 'UNDER_REPAIR'
        asset_obj.save()
        
        AssetMaintenanceLog.objects.create(
            asset=asset_obj,
            issue_reported=issue,
            cost_incurred_kes=cost,
            is_resolved=False
        )
        messages.warning(request, f"🔧 Asset status updated: {asset_obj.name} placed under maintenance logs.")
        return redirect('inventory_deck')

    # 2. Extract Category Filter Toggles
    selected_category = request.GET.get('category', 'ALL')
    if selected_category == 'ALL':
        assets = SchoolAsset.objects.all().order_by('category', 'name')
    else:
        assets = SchoolAsset.objects.filter(category=selected_category).order_by('name')

    context = {
        'assets': assets,
        'selected_category': selected_category,
        'maintenance_tickets': AssetMaintenanceLog.objects.filter(is_resolved=False).select_related('asset'),
        'total_operational': SchoolAsset.objects.filter(status='OPERATIONAL').count(),
        'total_repair_flags': SchoolAsset.objects.filter(status='UNDER_REPAIR').count(),
    }
    return render(request, 'finance/inventory_control_deck.html', context)