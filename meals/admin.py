from django.contrib import admin
from django.contrib import admin
from django import forms
from django.contrib.admin import AdminSite
from .models import MealRecord, Student, ClassRoom, StudentPayment
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.urls import reverse
admin.site.site_header  = "Trang quản trị bữa ăn học sinh"
admin.site.site_title   = "Quản lý bữa ăn"
admin.site.index_title  = "Bảng điều khiển"
class MyAdminSite(AdminSite):
    site_header = "Trang quản trị bữa ăn học sinh"
    index_title = "Bảng điều khiển"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Đổ nhanh 2 link vào dashboard
        extra_context['quick_links'] = [
            {
                'url': reverse('meals:statistics'),
                'label': '📊 Thống kê'
            },
            {
                'url': reverse('meals:student_payment_edit'),
                'label': '💳 Chỉnh sửa công nợ'
            }
        ]
        return super().index(request, extra_context)

    # Tuỳ ý bạn có thể override get_urls để thêm view custom,
    # nhưng ở đây chỉ cần index.

class ClassNameFilter(admin.SimpleListFilter):
    title = 'Lớp học'
    parameter_name = 'class_name'

    def lookups(self, request, model_admin):
        class_names = Student.objects.values_list('class_name', flat=True).distinct()
        return [(cls, cls) for cls in class_names if cls]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(class_name=self.value())
        return queryset

class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    # Đổi tên hiển thị của model ClassRoom trong Admin
    verbose_name = "Lớp học"
    verbose_name_plural = "Các lớp học"

class StudentAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = ('classroom',)
    # Đổi tên hiển thị của model Student trong Admin
    verbose_name = "Học sinh"
    verbose_name_plural = "Các học sinh"

class MealRecordAdmin(admin.ModelAdmin):
    change_list_template = "admin/meals/mealrecord/change_list.html"
    list_display = ('student', 'date', 'meal_type', 'status')
    fields = ('student','date','meal_type','status','non_eat','absence_reason')
    list_filter = ('date', 'meal_type')
    search_fields = ('student__name',)
    # Đổi tên hiển thị của model MealRecord trong Admin
    verbose_name = "Bữa ăn"
    verbose_name_plural = "Các bữa ăn"

    def save_model(self, request, obj, form, change):
        """
        Trước khi lưu, kiểm tra xem đã có MealRecord nào với cùng học sinh, ngày và loại bữa ăn chưa.
        Nếu có, cập nhật lại status; nếu không có, tạo mới.
        Sau đó, sử dụng câu lệnh SQL một dòng để cập nhật remaining_balance của StudentPayment tương ứng
        với học sinh và tháng của obj.date theo công thức:
        
        remaining_balance = amount_paid - tuition_fee - total_meal_charge + (remaining_balance tháng trước, 0 nếu không có)
        
        Trong đó total_meal_charge được tính theo:
          - Mỗi bữa sáng: 10
          - Mỗi bữa trưa: nếu daily_meal_fee = 30 thì 20, nếu = 40 thì 30, nếu khác thì (daily_meal_fee - 10)
        Chỉ tính tiền với các bữa có status "Đủ" hoặc (status "Thiếu" và non_eat = 2).
        """
        existing_record = MealRecord.objects.filter(
            student=obj.student,
            date=obj.date,
            meal_type=obj.meal_type
        ).first()

        if existing_record:
            existing_record.status = obj.status
            existing_record.non_eat = obj.non_eat  # Cập nhật non_eat
            existing_record.save()
        else:
            super().save_model(request, obj, form, change)
        
        # Xác định chuỗi "YYYY-MM" từ obj.date
        year_month = obj.date.strftime("%Y-%m")
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("UPDATE meals_studentpayment SET remaining_balance = amount_paid - tuition_fee - (SELECT COALESCE(SUM(CASE WHEN meal_type = 'Bữa sáng' AND (status = 'Đủ' OR (status = 'Thiếu' AND non_eat = 2)) THEN 10000 WHEN meal_type = 'Bữa trưa' AND (status = 'Đủ' OR (status = 'Thiếu' AND non_eat = 2)) THEN CASE WHEN meals_studentpayment.daily_meal_fee = 30000 THEN 20000 WHEN meals_studentpayment.daily_meal_fee = 40000 THEN 30000 ELSE meals_studentpayment.daily_meal_fee - 10000 END ELSE 0 END), 0) FROM meals_mealrecord WHERE meals_mealrecord.student_id = meals_studentpayment.student_id AND strftime('%%Y-%%m', meals_mealrecord.date) = meals_studentpayment.month) + COALESCE((SELECT sp_prev.remaining_balance FROM meals_studentpayment AS sp_prev WHERE sp_prev.student_id = meals_studentpayment.student_id AND sp_prev.month = strftime('%%Y-%%m', date(meals_studentpayment.month || '-01', '-1 month')) ORDER BY sp_prev.id DESC LIMIT 1), 0) WHERE student_id = %s AND month = %s;", [obj.student.id, year_month])
class MealRecordAdminForm(forms.ModelForm):
    class Meta:
        model = MealRecord
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 1) disable non_eat nếu status="Đủ"
        if self.instance and self.instance.status == "Đủ":
            self.fields['non_eat'].disabled = True
        # 2) ẩn luôn absence_reason nếu non_eat==0
        if self.instance and self.instance.non_eat == 0:
            self.fields.pop('absence_reason', None)
admin.site.register(ClassRoom, ClassRoomAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(MealRecord, MealRecordAdmin)
# Khởi tạo site mới
my_admin_site = MyAdminSite(name='myadmin')

# Đăng ký các model với site mới
from .admin import MealRecordAdmin  # form tuỳ chỉnh bạn đã có
my_admin_site.register(MealRecord, MealRecordAdmin)
my_admin_site.register(Student)
my_admin_site.register(ClassRoom)
# Đăng ký thêm StudentPayment nếu muốn
my_admin_site.register(StudentPayment)
my_admin_site.register(User, UserAdmin)
my_admin_site.register(Group, GroupAdmin)