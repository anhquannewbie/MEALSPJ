from django import forms
from .models import MealRecord, Student

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
