from django import forms
from .models import FeeReceipt, Student

class ReceiptEntryForm(forms.ModelForm):
    student_admission = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Student Admission Number'})
    )

    class Meta:
        model = FeeReceipt
        fields = ['reference_code', 'amount_paid', 'payment_channel']
        widgets = {
            'reference_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. QRE789XYZ'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'payment_channel': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_student_admission(self):
        adm_no = self.cleaned_data.get('student_admission', '').strip()
        if not Student.objects.filter(admission_number=adm_no, is_active=True).exists():
            raise forms.ValidationError("No active student found with this admission number.")
        return adm_no
