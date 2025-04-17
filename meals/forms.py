from django import forms
from .models import MealRecord, Student,ClassRoom
from .models import StudentPayment

class StudentPaymentForm(forms.ModelForm):
    classroom = forms.ChoiceField(
        required=False,
        label='Lớp',
        choices=[]
    )
    month = forms.DateField(
        label='Tháng (YYYY-MM)',
        widget=forms.DateInput(attrs={'type': 'month'}),
        input_formats=['%Y-%m']
    )
    prev_month_balance = forms.DecimalField(
        label="Công nợ",
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )
    current_month_payment = forms.DecimalField(
        label="Tiền tháng này",
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )

    class Meta:
        model = StudentPayment
        fields = [
            'classroom',
            'student',
            'month',
            'tuition_fee',
            'daily_meal_fee',
            'amount_paid',
        ]
        labels = {
            'classroom':      'Chọn Lớp',
            'student':        'Học sinh',
            'tuition_fee':    'Học phí',
            'daily_meal_fee': 'Tiền ăn/ngày',
            'amount_paid':    'Tiền đã đóng',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Lấy danh sách lớp
        cls_list = ClassRoom.objects.values_list('id','name')
        self.fields['classroom'].choices = [('', '--- Chọn Lớp ---')] + [
            (str(pk), name) for pk,name in cls_list
        ]
        # Student rỗng ban đầu
        self.fields['student'].queryset = Student.objects.none()

        # Nếu POST có class, load student
        if 'classroom' in self.data:
            try:
                cid = int(self.data.get('classroom'))
                self.fields['student'].queryset = Student.objects.filter(
                    classroom_id=cid
                ).order_by('name')
            except:
                pass
        elif self.instance.pk:
            cid = self.instance.student.classroom_id
            self.fields['classroom'].initial = cid
            self.fields['student'].queryset = Student.objects.filter(
                classroom_id=cid
            ).order_by('name')

        # Tính công nợ (prev_month_balance)
        if self.instance and self.instance.pk and self.instance.month:
            dt = datetime.strptime(self.instance.month, '%Y-%m')
            prev_m = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
            from .models import StudentPayment as SP
            prev = SP.objects.filter(
                student=self.instance.student,
                month=prev_m
            ).order_by('-id').first()
            self.fields['prev_month_balance'].initial = (
                prev.remaining_balance if prev and prev.remaining_balance is not None else 0
            )
        else:
            self.fields['prev_month_balance'].initial = 0

    def clean_month(self):
        # month coming in as a datetime.date from DateField
        dt = self.cleaned_data['month']
        return dt.strftime('%Y-%m')  # trả về string lưu vào model CharField
class MealRecordForm(forms.ModelForm):
    class_name_choice = forms.ChoiceField(
        label="Lớp học",
        required=True,
        choices=[],
    )
    non_eat = forms.ChoiceField(
        label="Trạng thái nghỉ ăn",
        choices=[(0, 'Ăn đủ'), (1, 'Nghỉ (Có phép)'), (2, 'Nghỉ (Không phép)')],
        required=True
    )

    class Meta:
        model = MealRecord
        fields = ['class_name_choice', 'student', 'date', 'meal_type', 'status', 'non_eat']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'student': 'Học Sinh',
        }
    def __init__(self, *args, **kwargs):
        super(MealRecordForm, self).__init__(*args, **kwargs)
        # Lấy tất cả các lớp học trong bảng Student.
        class_choices = Student.objects.values_list('class_name', flat=True).distinct()
        choices = [('', 'Chọn Lớp')] + [(cls, cls) for cls in class_choices]
        self.fields['class_name_choice'].choices = choices

        # Nếu có dữ liệu từ request, cập nhật queryset cho trường student.
        if 'class_name_choice' in self.data:
            selected_class = self.data.get('class_name_choice')
            try:
                self.fields['student'].queryset = Student.objects.filter(class_name=selected_class).order_by('name')
            except (ValueError, TypeError):
                self.fields['student'].queryset = Student.objects.none()
        elif self.instance.pk:
            self.fields['student'].queryset = Student.objects.filter(class_name=self.instance.student.class_name).order_by('name')
        else:
            self.fields['student'].queryset = Student.objects.none()
