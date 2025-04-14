from django import forms
from .models import MealRecord, Student,ClassRoom
from .models import StudentPayment

class StudentPaymentForm(forms.ModelForm):
    classroom = forms.ChoiceField(required=False, label='Lớp', choices=[])
    prev_month_balance = forms.DecimalField(
        label="Tiền tháng trước",
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
            # Không có previous_balance, vì đã xóa
            # Không có remaining_balance, vì DB field hiển thị qua field ảo current_month_payment
        ]
        labels = {
            'classroom': 'Chọn Lớp',
            'student': 'Học sinh',
            'month': 'Tháng (YYYY-MM)',
            'tuition_fee': 'Học phí',
            'daily_meal_fee': 'Tiền ăn/ngày',
            'amount_paid': 'Tiền đã đóng',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Lấy danh sách ClassRoom
        from .models import ClassRoom, Student
        classrooms = ClassRoom.objects.values_list('id', 'name')
        self.fields['classroom'].choices = [('', '--- Chọn Lớp ---')] + [
            (str(cls_id), cls_name) for cls_id, cls_name in classrooms
        ]
        # Mặc định student là none
        self.fields['student'].queryset = Student.objects.none()

        # Xử lý logic lọc học sinh theo lớp
        if 'classroom' in self.data:
            try:
                class_id = int(self.data.get('classroom'))
                self.fields['student'].queryset = Student.objects.filter(classroom_id=class_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            # Nếu đang edit 1 payment đã có sẵn
            class_id = self.instance.student.classroom_id
            self.fields['classroom'].initial = class_id
            self.fields['student'].queryset = Student.objects.filter(classroom_id=class_id).order_by('name')

        # Nếu instance có pk -> hiển thị "Tiền tháng trước" đã được dùng để tính
        # => Tức là remaining_balance của tháng trước. 
        # Ta tính logic y như save() => Tìm record tháng trước, lấy remaining_balance
        if self.instance and self.instance.pk:
            from datetime import datetime, timedelta
            if self.instance.month:
                dt = datetime.strptime(self.instance.month, '%Y-%m')
                prev_month = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
                from .models import StudentPayment
                prev_payment = StudentPayment.objects.filter(
                    student=self.instance.student,
                    month=prev_month
                ).order_by('-id').first()
                if prev_payment:
                    self.fields['prev_month_balance'].initial = prev_payment.remaining_balance or 0
                else:
                    self.fields['prev_month_balance'].initial = 0
        else:
            # Nếu tạo mới => mặc định = 0
            self.fields['prev_month_balance'].initial = 0
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
