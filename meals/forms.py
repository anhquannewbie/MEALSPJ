from django import forms
from .models import MealRecord, Student, ClassRoom, StudentPayment, MealPrice
from datetime import timedelta, datetime
from decimal import Decimal

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
        label="Công nợ tháng trước",
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
    remaining_balance = forms.DecimalField(
        label="Số dư hiện tại",
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
            'meal_price',
            'amount_paid',
        ]
        labels = {
            'classroom':      'Chọn Lớp',
            'student':        'Học sinh',
            'tuition_fee':    'Học phí',
            'meal_price':     'Cấu hình giá ăn',
            'amount_paid':    'Tiền đã đóng',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1) MealPrice dropdown + initial
        qs = MealPrice.objects.all()
        self.fields['meal_price'].queryset = qs
        if not (self.instance and self.instance.pk):
            latest = qs.first()
            if latest:
                self.fields['meal_price'].initial = latest.pk

        # 2) Classroom → student dynamic
        cls_list = ClassRoom.objects.values_list('id', 'name')
        self.fields['classroom'].choices = [('', '--- Chọn Lớp ---')] + [
            (str(pk), name) for pk, name in cls_list
        ]
        self.fields['student'].queryset = Student.objects.none()
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

        # 3) Tính công nợ tháng trước
        if self.instance and self.instance.pk and self.instance.month:
            dt = datetime.strptime(self.instance.month, '%Y-%m')
            prev_m = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
            prev_sp = StudentPayment.objects.filter(
                student=self.instance.student,
                month=prev_m
            ).order_by('-id').first()
            prev_balance = (prev_sp.remaining_balance
                            if prev_sp and prev_sp.remaining_balance is not None
                            else Decimal('0'))
            self.fields['prev_month_balance'].initial = prev_balance
        else:
            self.fields['prev_month_balance'].initial = Decimal('0')

        # 4) Tính Tiền tháng này & Số dư hiện tại
        if self.instance and self.instance.pk and self.instance.month:
            sp = StudentPayment.objects.get(pk=self.instance.pk)

            # recompute prev_balance safely
            try:
                dt = datetime.strptime(self.instance.month, '%Y-%m')
                prev_m = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
                prev_sp = StudentPayment.objects.filter(
                    student=self.instance.student,
                    month=prev_m
                ).order_by('-id').first()
                prev_balance = (prev_sp.remaining_balance
                                if prev_sp and prev_sp.remaining_balance is not None
                                else Decimal('0'))
            except:
                prev_balance = Decimal('0')

            amt_paid    = sp.amount_paid or Decimal('0')
            tuition     = sp.tuition_fee  or Decimal('0')
            rem_bal     = sp.remaining_balance or Decimal('0')

            # meal_total = (paid + prev_balance) - (tuition + remaining)
            meal_total = (amt_paid + prev_balance) - (tuition + rem_bal)
            current    = tuition + meal_total

            self.fields['current_month_payment'].initial = current.quantize(Decimal('0.01'))
            self.fields['remaining_balance'].initial    = rem_bal
        else:
            self.fields['current_month_payment'].initial = Decimal('0')
            self.fields['remaining_balance'].initial    = Decimal('0')

    def clean_month(self):
        dt = self.cleaned_data['month']
        return dt.strftime('%Y-%m')


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
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}
        labels = {'student': 'Học Sinh'}

    def __init__(self, *args, **kwargs):
        super(MealRecordForm, self).__init__(*args, **kwargs)
        class_choices = Student.objects.values_list('classroom__name', flat=True).distinct()
        choices = [('', 'Chọn Lớp')] + [(cls, cls) for cls in class_choices]
        self.fields['class_name_choice'].choices = choices

        if 'class_name_choice' in self.data:
            sel = self.data.get('class_name_choice')
            try:
                self.fields['student'].queryset = Student.objects.filter(
                    classroom__name=sel
                ).order_by('name')
            except (ValueError, TypeError):
                self.fields['student'].queryset = Student.objects.none()
        elif self.instance.pk:
            self.fields['student'].queryset = Student.objects.filter(
                classroom=self.instance.student.classroom
            ).order_by('name')
        else:
            self.fields['student'].queryset = Student.objects.none()
