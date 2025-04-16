from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
class StudentPayment(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    month = models.CharField(max_length=7, help_text="YYYY-MM")
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2)
    daily_meal_fee = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Tính số dư tháng trước như cũ
        prior_remain_balance = 0
        if self.month:
            dt = datetime.strptime(self.month, '%Y-%m')
            prev_month = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
            prev_payment = StudentPayment.objects.filter(student=self.student, month=prev_month).order_by('-id').first()
            if prev_payment and prev_payment.remaining_balance:
                prior_remain_balance = prev_payment.remaining_balance

        # Tính tổng tiền ăn thực tế dựa trên MealRecord của tháng hiện tại
        # Ta tách year và month từ self.month
        try:
            year_str, month_str = self.month.split("-")
            year = int(year_str)
            month = int(month_str)
        except Exception:
            year = None
            month = None
        total_meal_charge = 0
        if year and month:
            # Lấy các bản ghi MealRecord cho học sinh trong tháng (chỉ tính các bữa sáng và bữa trưa)
            meal_records = self.student.mealrecord_set.filter(date__year=year, date__month=month, meal_type__in=["Bữa sáng", "Bữa trưa"])
        else:
            meal_records = []

        # Xác định tiền cho từng bữa dựa trên daily_meal_fee
        # Giá trị mặc định: bữa sáng luôn tính 10
        fee_breakfast = 10
        if self.daily_meal_fee == 30:
            fee_lunch = 20
        elif self.daily_meal_fee == 40:
            fee_lunch = 30
        else:
            # Nếu daily_meal_fee khác, dùng công thức: bữa trưa = daily_meal_fee - 10
            fee_lunch = float(self.daily_meal_fee) - 10

        # Duyệt qua các MealRecord của tháng
        for record in meal_records:
            if record.meal_type == "Bữa sáng":
                # Nếu ăn đủ hoặc (không đủ và nghỉ không phép), tính phí bữa sáng; nếu nghỉ có phép thì không tính
                if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                    total_meal_charge += fee_breakfast
                # Nếu nghỉ có phép, thêm 0
            elif record.meal_type == "Bữa trưa":
                if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                    total_meal_charge += fee_lunch

        # Cập nhật remaining_balance theo công thức mới:
        # remaining_balance = amount_paid - tuition_fee - total_meal_charge + prior_remain_balance
        self.remaining_balance = self.amount_paid - self.tuition_fee - Decimal(total_meal_charge) + prior_remain_balance

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
