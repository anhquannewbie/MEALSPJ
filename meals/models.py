from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
class StudentPayment(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    month = models.CharField(max_length=7, help_text="YYYY-MM")
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2)
    daily_meal_fee = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        
        # Chúng ta giả định vẫn cố định 26 ngày
        days = 26
        
        # Tính số dư tháng trước:
        prior_remain_balance = 0
        
        if self.month:
            # month ở format YYYY-MM
            dt = datetime.strptime(self.month, '%Y-%m')
            # Xác định tháng trước
            prev_month = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
            
            # Tìm bản ghi tháng trước, nếu có
            prev_payment = StudentPayment.objects.filter(
                student=self.student,
                month=prev_month
            ).order_by('-id').first()
            
            if prev_payment and prev_payment.remaining_balance:
                prior_remain_balance = prev_payment.remaining_balance
        
        # Tính remaining_balance = số tiền đóng - tiền học phí - tiền ăn (26 ngày) + số dư tháng trước
        self.remaining_balance = (
            self.amount_paid
            - self.tuition_fee
            - (self.daily_meal_fee * days)
            + prior_remain_balance
        )
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.month}"
class ClassRoom(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="Tên lớp học")

    def __str__(self):
        return self.name
class Student(models.Model):
    name = models.CharField(max_length=100, help_text="Họ và tên học sinh")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, help_text="Lớp học của học sinh")

    def __str__(self):
        return f"{self.name} ({self.classroom})"

class MealRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(help_text="Ngày của bữa ăn")
    MEAL_TYPE_CHOICES = [
        ('Bữa sáng', 'Bữa sáng'),
        ('Bữa trưa', 'Bữa trưa'),
        # Loại bỏ "Bữa xế" nếu bạn không sử dụng nữa
    ]
    meal_type = models.CharField(max_length=50, choices=MEAL_TYPE_CHOICES, help_text="Chọn loại bữa ăn")
    # Nếu ăn đủ thì status là "Đủ", còn nếu nghỉ thì status là "Thiếu"
    # Nhưng giờ chúng ta bổ sung thêm cột non_eat để phân biệt nghỉ có phép và không phép.
    status = models.CharField(
        max_length=20,
        choices=[('Đủ', 'Đủ'), ('Thiếu', 'Thiếu')],
        help_text="Trạng thái bữa ăn"
    )
    # Thêm trường non_eat: 0 = Ăn đủ; 1 = Nghỉ có phép; 2 = Nghỉ không phép.
    non_eat = models.IntegerField(
        default=0,
        choices=[(0, 'Ăn đủ'), (1, 'Nghỉ (Có phép)'), (2, 'Nghỉ (Không phép)')],
        help_text="Loại trừ bữa ăn: 0 = Ăn đủ, 1 = Nghỉ (Có phép), 2 = Nghỉ (Không phép)"
    )

    def __str__(self):
        return f"{self.student.name} - {self.meal_type} - {self.date}"
