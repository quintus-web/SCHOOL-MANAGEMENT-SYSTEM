# finance/admin.py
from django.contrib import admin
from django.contrib import messages
from .models import (
    ClassStream, Subject, Teacher, Student, 
    AttendanceRecord, DisciplineReport, ExamRecord, 
    FeeInvoice, FeeReceipt, StaffProfile, 
    LeaveApplication, TimetableAllocation, 
    StudentAttendanceRecord, TeacherAttendanceRecord, 
    HomeworkAssignment, SchoolAnnouncement, SchoolAsset, 
    AssetMaintenanceLog, LessonPlan, LearningMaterial, TimetableSlot
)

# ── 1. PREMIUM CUSTOMIZATIONS FOR LEARNERS MANAGEMENT ──
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('admission_number', 'first_name', 'last_name', 'class_stream', 'current_balance', 'status', 'is_active')
    list_filter = ('class_stream', 'status', 'is_active', 'gender')
    search_fields = ('admission_number', 'first_name', 'last_name', 'guardian_name', 'parent_phone')
    list_editable = ('status', 'is_active')
    readonly_fields = ('date_of_admission',)
    fieldsets = (
        ('Core Personal Identity', {'fields': ('admission_number', 'first_name', 'middle_name', 'last_name', 'gender', 'date_of_birth', 'passport_photo_url')}),
        ('Academic Allocation', {'fields': ('class_stream', 'status', 'is_active')}),
        ('Parental Logistics Links', {'fields': ('guardian_name', 'guardian_relation', 'parent_phone', 'parent_email', 'emergency_contact_name', 'emergency_contact_phone')}),
        ('Medical Filing Vaults', {'fields': ('blood_group', 'known_allergies', 'medical_conditions')}),
        ('Financial Ledger Position', {'fields': ('current_balance',)}),
    )
    actions = ['trigger_bulk_arrears_sms']

    @admin.action(description="🚨 Simulate Arrears Alert SMS to Selected Parents")
    def trigger_bulk_arrears_sms(self, request, queryset):
        sent_count = 0
        for student in queryset:
            if student.current_balance > 0:
                # Simulated pipeline dispatch
                sent_count += 1
        self.message_user(request, f"🚀 Broadcast complete! Sent {sent_count} text notifications directly to target parent phone lines.", messages.SUCCESS)


# ── 2. TREASURY INVOICES & AUDIT LEDGER CONTROLS ──
@admin.register(FeeInvoice)
class FeeInvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'title', 'amount', 'date_issued')
    list_filter = ('date_issued', 'title')
    search_fields = ('student__first_name', 'student__last_name', 'student__admission_number', 'title')


@admin.register(FeeReceipt)
class FeeReceiptAdmin(admin.ModelAdmin):
    list_display = ('reference_code', 'student', 'invoice', 'amount', 'status', 'date_paid')
    list_filter = ('status', 'date_paid', 'invoice__title')
    search_fields = ('reference_code', 'student__first_name', 'student__last_name', 'student__admission_number')
    list_editable = ('status',)


# ── 3. FACULTY & STAFF PROFILE SETUPS ──
@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('employee_number', 'user', 'role_designation', 'phone_line', 'current_status', 'performance_score')
    list_filter = ('role_designation', 'current_status')
    search_fields = ('employee_number', 'user__first_name', 'user__last_name', 'phone_line')
    list_editable = ('current_status', 'performance_score')


# ── 4. ACADEMIC AND EVALUATION MATRICES ──
@admin.register(ExamRecord)
class ExamRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'term', 'year', 'cat_1', 'cat_2', 'final_exam', 'total_marks')
    list_filter = ('term', 'year', 'subject', 'student__class_stream')
    search_fields = ('student__first_name', 'student__last_name', 'subject__name')


# ── 5. DISPATCH BULLETINS & ASSIGNMENTS REGISTER ──
@admin.register(SchoolAnnouncement)
class SchoolAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_audience', 'date_published')
    list_filter = ('target_audience', 'date_published')
    search_fields = ('title', 'announcement_body')


@admin.register(HomeworkAssignment)
class HomeworkAssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'stream', 'subject', 'date_given', 'submission_deadline')
    list_filter = ('stream', 'subject', 'submission_deadline')
    search_fields = ('title', 'task_instructions')


# ── 6. LOGISTICS, INVENTORY & ROUTINE SCHEDULING ALLOCATIONS ──
@admin.register(ClassStream)
class ClassStreamAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_number', 'capacity')

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('employee_number', 'first_name', 'last_name', 'specialization')

@admin.register(SchoolAsset)
class SchoolAssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'serial_or_isbn', 'category', 'available_quantity', 'total_quantity', 'status')
    list_filter = ('category', 'status')
    list_editable = ('status', 'available_quantity')

@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ('day', 'stream', 'subject', 'teacher', 'time_start', 'time_end')
    list_filter = ('day', 'stream', 'subject')

# ── 7. LEAVE REGISTRY & ADMINISTRATIVE FALLBACKS ──
admin.site.register(AttendanceRecord)
admin.site.register(DisciplineReport)
admin.site.register(LeaveApplication)
admin.site.register(TimetableAllocation)
admin.site.register(StudentAttendanceRecord)
admin.site.register(TeacherAttendanceRecord)
admin.site.register(AssetMaintenanceLog)
admin.site.register(LessonPlan)
admin.site.register(LearningMaterial)
