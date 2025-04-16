from django.contrib import admin
from .models import Student, MealRecord, ClassRoom, StudentPayment

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

class StudentAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = ('classroom',)

class MealRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'meal_type', 'status')
    list_filter = ('date', 'meal_type')
    search_fields = ('student__name',)

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

admin.site.register(ClassRoom, ClassRoomAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(MealRecord, MealRecordAdmin)
