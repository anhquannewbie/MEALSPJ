from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Người dùng",
        related_name='audit_logs'
    )
    action = models.CharField(
        max_length=100,
        verbose_name="Hành động"
    )
    path = models.CharField(
        max_length=200,
        verbose_name="Đường dẫn"
    )
    data = models.TextField(
        blank=True,
        verbose_name="Dữ liệu"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Thời gian"
    )

    class Meta:
        verbose_name        = "Audit log"
        verbose_name_plural = "Các bản ghi audit"
    def __str__(self):
        return f"{self.timestamp} | {self.user or '—'} | {self.action}"
class MealPrice(models.Model):
    effective_date  = models.DateField(
        default=timezone.now,
        help_text="Ngày bắt đầu áp dụng mức giá này"
    )
    daily_price     = models.PositiveIntegerField(
        default=30000,
        help_text="Giá tiền ăn 1 ngày (VND)"
    )
    breakfast_price = models.PositiveIntegerField(
        default=15000,
        help_text="Giá tiền bữa sáng (VND)"
    )
    lunch_price     = models.PositiveIntegerField(
        default=15000,
        help_text="Giá tiền bữa trưa (VND)"
    )

    class Meta:
        ordering = ['-effective_date']
        verbose_name = "Cấu hình giá ăn"
        verbose_name_plural = "Các cấu hình giá ăn"

    def __str__(self):
        return f"{self.effective_date:%Y-%m-%d} → {self.daily_price:,}₫/ngày"
class StudentPayment(models.Model):
    class Meta:
        ordering = ['-id']
        unique_together = ('student', 'month')
        verbose_name = "Công nợ học sinh"
        verbose_name_plural = "Công nợ học sinh"
        permissions = [
            ("view_statistics", "Có thể xem thống kê"),
        ]
    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        verbose_name="Học sinh"
    )
    month = models.CharField(
        max_length=7,
        verbose_name="Tháng",
        help_text="Chọn tháng theo định dạng YYYY‑MM"
    )
    tuition_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Học phí"
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Số tiền đã đóng"
    )
    remaining_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Số dư"
    )
    meal_price = models.ForeignKey(
        MealPrice,
        on_delete=models.PROTECT,
        verbose_name="Cấu hình giá ăn",
        help_text="Chọn cấu hình giá ăn áp dụng cho tháng này"
    )
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

        # Lấy giá động từ FK meal_price
        fee_breakfast = self.meal_price.breakfast_price
        fee_lunch     = self.meal_price.lunch_price

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
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Tên lớp học"
    )
    # đổi sang học kỳ/niên khóa tuỳ ý
    term = models.CharField(
        "Học kỳ/Niên khoá",
        max_length=20,
        help_text="Ví dụ: 2025-2026, Hè 2026,…"
    )

    def __str__(self):
        return f"{self.name} ({self.term})"
    class Meta:
        ordering = ['-id']
        verbose_name = _('Lớp học')
        verbose_name_plural = _('Lớp học')
        # Đảm bảo trong cùng 1 năm, không có 2 lớp trùng tên
        unique_together = ('name', 'term')
class Student(models.Model):
    name = models.CharField(max_length=100, help_text="Họ và tên học sinh")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, help_text="Lớp học của học sinh")

    def __str__(self):
        return f"{self.name} ({self.classroom})"
    class Meta:
        ordering = ['-id']
        verbose_name = _('Học sinh')
        verbose_name_plural = _('Học sinh')
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
    absence_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Lý do nghỉ"
    )
    def __str__(self):
        return f"{self.student.name} - {self.meal_type} - {self.date}"
    class Meta:
        ordering = ['-id']
        verbose_name = _("Bữa ăn")                # tên số ít
        verbose_name_plural = _("Bữa ăn")         # tên số nhiều (hiển thị ở admin)
