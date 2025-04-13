from django.db import models
from django.utils import timezone

class StudentPayment(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    month = models.CharField(max_length=7, help_text="YYYY-MM")
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2)
    daily_meal_fee = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    # previous_balance tự động lấy từ DB, nhưng vẫn lưu vào đây
    previous_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Giả định cố định 26 ngày
        days = 26
        self.remaining_balance = self.amount_paid - self.tuition_fee - (self.daily_meal_fee * days) + self.previous_balance
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
        ('Bữa xế', 'Bữa xế'),
    ]
    meal_type = models.CharField(max_length=50, choices=MEAL_TYPE_CHOICES, help_text="Chọn loại bữa ăn")
    status = models.CharField(
        max_length=20,
        choices=[('Đủ', 'Đủ'), ('Thiếu', 'Thiếu')],
        help_text="Trạng thái bữa ăn"
    )

    def __str__(self):
        return f"{self.student.name} - {self.meal_type} - {self.date}"
