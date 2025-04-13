from django import forms
from .models import MealRecord, Student,ClassRoom
from .models import StudentPayment

class StudentPaymentForm(forms.ModelForm):
    classroom = forms.ChoiceField(required=False, label='Lớp', choices=[])

    class Meta:
        model = StudentPayment
        fields = ['classroom', 'student', 'month', 'tuition_fee', 'daily_meal_fee', 'amount_paid', 'previous_balance']
        labels = {
            'classroom': 'Chọn Lớp',
            'student': 'Học sinh',
            'month': 'Tháng (YYYY-MM)',
            'tuition_fee': 'Học phí',
            'daily_meal_fee': 'Tiền ăn/ngày',
            'amount_paid': 'Tiền đã đóng',
            'previous_balance': 'Tiền tháng trước (tự động)',
        }
        # Đánh dấu previous_balance là readonly (HTML) bằng widget
        widgets = {
            'previous_balance': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lấy toàn bộ lớp
        classrooms = ClassRoom.objects.values_list('id', 'name')
        # Tạo choices cho classroom
        self.fields['classroom'].choices = [('', '--- Chọn Lớp ---')] + [(str(cls_id), cls_name) for cls_id, cls_name in classrooms]

        # Mặc định student là none (chưa chọn lớp)
        self.fields['student'].queryset = Student.objects.none()

        # Nếu có dữ liệu POST => xem classroom đã chọn
        if 'classroom' in self.data:
            try:
                class_id = int(self.data.get('classroom'))
                self.fields['student'].queryset = Student.objects.filter(classroom_id=class_id).order_by('name')
            except (ValueError, TypeError):
                pass
        # Hoặc nếu đang sửa 1 bản ghi có sẵn => tự động set classroom
        elif self.instance.pk:
            class_id = self.instance.student.classroom_id
            self.fields['classroom'].initial = class_id
            self.fields['student'].queryset = Student.objects.filter(classroom_id=class_id).order_by('name')
class MealRecordForm(forms.ModelForm):
    # Thêm trường chọn lớp học: không lưu vào model, dùng để lọc học sinh.
    class_name_choice = forms.ChoiceField(
        label="Lớp học",
        required=True,
        choices=[],
    )

    class Meta:
        model = MealRecord
        fields = ['class_name_choice', 'student', 'date', 'meal_type', 'status']
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
