from django.db import models

class Student(models.Model):
    name = models.CharField(max_length=100, help_text="Họ và tên học sinh")
    class_name = models.CharField(max_length=20, help_text="Lớp học (ví dụ: Tiger 1, Tiger 2, PIG. CAT, BIRD 1, BIRD 2, BEE)")

    def __str__(self):
        return f"{self.name} ({self.class_name})"

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
        choices=[('Đủ', 'Đủ'), ('Thiếu', 'Thiếu'), ('Bổ sung', 'Bổ sung')],
        help_text="Trạng thái bữa ăn"
    )

    def __str__(self):
        return f"{self.student.name} - {self.meal_type} - {self.date}"
