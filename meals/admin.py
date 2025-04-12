from django.contrib import admin
from .models import Student, MealRecord

class ClassNameFilter(admin.SimpleListFilter):
    title = 'Lớp học'
    parameter_name = 'class_name'

    def lookups(self, request, model_admin):
        # Lấy ra các giá trị class_name khác nhau
        class_names = Student.objects.values_list('class_name', flat=True).distinct()
        return [(cls, cls) for cls in class_names if cls]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(class_name=self.value())
        return queryset
class StudentAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = (ClassNameFilter,)

class MealRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'meal_type', 'status')
    list_filter = ('date', 'meal_type')
    search_fields = ('student__name',)

    def save_model(self, request, obj, form, change):
        """
        Trước khi lưu, kiểm tra xem đã có MealRecord nào với cùng
        học sinh, ngày và loại bữa ăn chưa.
        Nếu có, cập nhật lại status, ngược lại tạo mới.
        """
        existing_record = MealRecord.objects.filter(
            student=obj.student,
            date=obj.date,
            meal_type=obj.meal_type
        ).first()
        if existing_record:
            # Cập nhật status của bản ghi đã tồn tại
            existing_record.status = obj.status
            existing_record.save()
        else:
            super().save_model(request, obj, form, change)

admin.site.register(Student, StudentAdmin)
admin.site.register(MealRecord, MealRecordAdmin)