# finance/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ClassStream(models.Model):
    name = models.CharField(max_length=50, unique=True)
    room_number = models.CharField(max_length=20, blank=True, null=True)
    capacity = models.IntegerField(default=40)

    def __str__(self):
        return self.name

class Subject(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.code})"

# Inside finance/models.py (Line 26)
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    employee_number = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15)
    # FIXED: Changed from SET_Null to SET_NULL
    specialization = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return f"Mwalimu {self.first_name} {self.last_name}"

class Student(models.Model):
    # Enums for clean lifecycle and medical states
    BLOOD_GROUPS = [('O+', 'O Positive'), ('O-', 'O Negative'), ('A+', 'A Positive'), ('A-', 'A Negative'), ('B+', 'B Positive'), ('AB+', 'AB Positive')]
    STATUS_CHOICES = [('ACTIVE', 'Active Learner'), ('TRANSFERRED', 'Transferred Out'), ('GRADUATED', 'Alumni / Graduated')]
    GENDER_CHOICES = [('M', 'Boy'), ('F', 'Girl')]

    # 1. Core Core Identity & Admission Info
    admission_number = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_admission = models.DateField(auto_now_add=True)
    passport_photo_url = models.URLField(max_length=500, blank=True, null=True, default="https://images.unsplash.com/photo-1597545558260-2dc35779abb7?q=80&w=200&auto=format&fit=crop")
    class_stream = models.ForeignKey(ClassStream, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    is_active = models.BooleanField(default=True)

    # 2. Comprehensive Parent / Guardian Fields
    guardian_name = models.CharField(max_length=100)
    guardian_relation = models.CharField(max_length=50, default="Parent")
    parent_phone = models.CharField(max_length=15)
    parent_email = models.EmailField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)

    # 3. Medical Records File Room
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUPS, blank=True, null=True)
    known_allergies = models.TextField(blank=True, null=True, default="None Registered")
    medical_conditions = models.TextField(blank=True, null=True, default="None")

    # 4. Financial Legacy Hook
    current_balance = models.DecimalField(max_length=10, decimal_places=2, default=0.00, max_digits=10)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.admission_number})"

class AttendanceRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField()
    is_present = models.BooleanField(default=True)
    remarks = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        unique_together = ('student', 'date')

class DisciplineReport(models.Model):
    SEVERITY_LEVELS = [('MINOR', 'Minor Infraction'), ('MEDIUM', 'Requires Guidance'), ('SEVERE', 'Suspension / Board Action')]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='discipline_logs')
    date_reported = models.DateField(auto_now_add=True)
    infraction_details = models.TextField()
    severity = models.CharField(max_length=15, choices=SEVERITY_LEVELS, default='MINOR')
    action_taken = models.CharField(max_length=200, default="Verbal Warning Given")

    def __str__(self):
        return f"{self.severity} - {self.student.last_name}"

class ExamRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    term = models.CharField(max_length=20, default='TERM_1')
    year = models.IntegerField(default=2026)
    cat_1 = models.IntegerField(default=0)
    cat_2 = models.IntegerField(default=0)
    final_exam = models.IntegerField(default=0)

    @property
    def total_marks(self):
        return self.cat_1 + self.cat_2 + self.final_exam

# Append to the absolute bottom of finance/models.py

class FeeInvoice(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_invoices')
    title = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_issued = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Invoice - {self.student.last_name} (KES {self.amount})"

class FeeReceipt(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_receipts')
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    # ... other fields ...
    STATUS_CHOICES = [('COMPLETED', 'Completed'), ('PENDING', 'Pending Verification'), ('FAILED', 'Failed')]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_receipts')
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateTimeField(auto_now_add=True)
    reference_code = models.CharField(max_length=50, unique=True) # e.g. M-Pesa Code
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='COMPLETED')

    def __str__(self):
        return f"Receipt {self.reference_code} - KES {self.amount}"
    
    # Append to the bottom of finance/models.py
from django.db import models
from django.contrib.auth.models import User

class StaffProfile(models.Model):
    ROLE_CHOICES = [
        ('PRINCIPAL', 'School Principal'),
        ('TEACHER', 'Class Teacher'),
        ('ACCOUNTANT', 'Bursar / Accountant'),
        ('SUPPORT', 'Support Staff'),
    ]
    STATUS_CHOICES = [
        ('ACTIVE', 'Active duty'),
        ('ON_LEAVE', 'On Sanctioned Leave'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    employee_number = models.CharField(max_length=30, unique=True)
    role_designation = models.CharField(max_length=20, choices=ROLE_CHOICES, default='TEACHER')
    phone_line = models.CharField(max_length=15, default="0700000000")
    specialization = models.CharField(max_length=100, default="Mathematics / Physics")
    base_salary_kes = models.DecimalField(max_digits=10, decimal_places=2, default=45000.00)
    current_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ACTIVE')
    performance_score = models.IntegerField(default=85) # Managed out of 100%

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_number})"

class LeaveApplication(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='leaves')
    leave_reason = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    is_approved = models.BooleanField(default=False)

class TimetableAllocation(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='classes_taught')
    stream = models.ForeignKey('ClassStream', on_delete=models.CASCADE)
    subject_title = models.CharField(max_length=50)
    weekday = models.CharField(max_length=15, default="Monday")
    time_slot = models.CharField(max_length=20, default="08:00 AM - 08:40 AM")

# Append to the bottom of finance/models.py
from django.db import models

class StudentAttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late with Excuse'),
    ]
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='attendance_history')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PRESENT')
    verification_method = models.CharField(max_length=30, default='BIOMETRIC_SCAN') # QR / FINGERPRINT
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'date')

class TeacherAttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('ON_LEAVE', 'Sanctioned Leave'),
    ]
    staff = models.ForeignKey('StaffProfile', on_delete=models.CASCADE, related_name='staff_attendance')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PRESENT')
    time_in = models.TimeField(null=True, blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('staff', 'date')

# Append to the bottom of finance/models.py

class HomeworkAssignment(models.Model):
    stream = models.ForeignKey('ClassStream', on_delete=models.CASCADE, related_name='assignments')
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    task_instructions = models.TextField()
    date_given = models.DateField(default=timezone.now)
    submission_deadline = models.DateField()

    def __str__(self):
        return f"{self.subject.name} - {self.title}"

class SchoolAnnouncement(models.Model):
    NOTICE_TARGETS = [
        ('ALL_PARENTS', 'All Parents'),
        ('FORM_1', 'Form 1 Stream Blocks Only'),
        ('FORM_2', 'Form 2 Stream Blocks Only'),
    ]
    title = models.CharField(max_length=200)
    announcement_body = models.TextField()
    target_audience = models.CharField(max_length=20, choices=NOTICE_TARGETS, default='ALL_PARENTS')
    date_published = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title
    
# Append to the bottom of finance/models.py

class SchoolAsset(models.Model):
    CATEGORY_CHOICES = [
        ('TEXTBOOKS', 'Textbook Inventory'),
        ('LAB_EQUIP', 'Computer & Lab Equipment'),
        ('FURNITURE', 'School Furniture Property'),
        ('STORES', 'General Store Supplies'),
    ]
    ASSET_STATUS = [
        ('OPERATIONAL', 'Operational / Active'),
        ('UNDER_REPAIR', 'Under Maintenance'),
        ('DECOMMISSIONED', 'Decommissioned / Written Off'),
    ]
    
    name = models.CharField(max_length=150)
    serial_or_isbn = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    total_quantity = models.PositiveIntegerField(default=1)
    available_quantity = models.PositiveIntegerField(default=1)
    assigned_location = models.CharField(max_length=100, help_text="e.g., Science Lab B, Form 2 Alpha Room")
    status = models.CharField(max_length=20, choices=ASSET_STATUS, default='OPERATIONAL')
    last_audited_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name}"

class AssetMaintenanceLog(models.Model):
    asset = models.ForeignKey(SchoolAsset, on_delete=models.CASCADE, related_name='maintenance_history')
    issue_reported = models.TextField()
    action_taken = models.TextField(blank=True, null=True)
    cost_incurred_kes = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date_logged = models.DateField(default=timezone.now)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Fix Log: {self.asset.name} on {self.date_logged}"
    
# Append to the bottom of finance/models.py

class LessonPlan(models.Model):
    teacher = models.ForeignKey('StaffProfile', on_delete=models.CASCADE, limit_choices_to={'role_designation': 'TEACHER'})
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    stream = models.ForeignKey('ClassStream', on_delete=models.CASCADE)
    topic = models.CharField(max_length=150)
    objectives = models.TextField(help_text="What will learners achieve by the end of this lesson?")
    week_number = models.PositiveIntegerField(default=1)
    date_planned = models.DateField()
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Week {self.week_number} - {self.subject.name}: {self.topic}"

class LearningMaterial(models.Model):
    MATERIAL_TYPES = [
        ('NOTES', 'Revision Notes'),
        ('PAST_PAPER', 'Past Examination Paper'),
        ('SYLLABUS', 'Curriculum Syllabus Guide'),
    ]
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    material_type = models.CharField(max_length=15, choices=MATERIAL_TYPES, default='NOTES')
    resource_url = models.URLField(help_text="Link to digital storage hosted notes or files (e.g., Google Drive/OneDrive)")
    date_uploaded = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_material_type_display()}] {self.title}"

class TimetableSlot(models.Model):
    DAYS_OF_WEEK = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
    ]
    stream = models.ForeignKey('ClassStream', on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey('StaffProfile', on_delete=models.CASCADE, limit_choices_to={'role_designation': 'TEACHER'})
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    time_start = models.TimeField()
    time_end = models.TimeField()

    def __str__(self):
        return f"{self.get_day_display()} | {self.time_start.strftime('%H:%M')} - {self.time_end.strftime('%H:%M')} ({self.subject.code})"

    # Inside finance/models.py
from django.db import models
from django.utils import timezone

class DailyAttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('SICK', 'Sick / Medical'),
        ('LEAVE', 'Authorized Leave'),
    ]
    
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='daily_attendance')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PRESENT')
    marked_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('student', 'date') # Enforces one check per learner per day
        ordering = ['-date', 'student__admission_number']

    def __str__(self):
        return f"{self.student.first_name} - {self.date} ({self.status})"
    
    # In finance/models.py
class DailyAttendanceRecord(models.Model):
    # ... existing fields ...
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    last_modified = models.DateTimeField(auto_now=True) # Automatically updates on save


# In finance/models.py

class DailyAttendanceRecord(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    date = models.DateField()  # <--- THIS IS WHAT YOU ARE MISSING
    status = models.CharField(max_length=20)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    last_modified = models.DateTimeField(auto_now=True)
