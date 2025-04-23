from django.contrib import admin
from django.contrib import admin
from django import forms
from django.contrib.admin import AdminSite
from .models import MealRecord, Student, ClassRoom, StudentPayment,MealPrice
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.contrib import messages
from openpyxl import Workbook, load_workbook
import csv
from django.urls import reverse
admin.site.site_header  = "Trang quản trị bữa ăn học sinh"
admin.site.site_title   = "Quản lý bữa ăn"
admin.site.index_title  = "Bảng điều khiển"

class MealPriceAdmin(admin.ModelAdmin):
    list_display  = ('effective_date', 'daily_price', 'breakfast_price', 'lunch_price')
    list_editable = ('daily_price', 'breakfast_price', 'lunch_price')
    list_filter   = ('effective_date',)
    ordering      = ('-effective_date',)
class StudentInline(admin.TabularInline):
    model = Student
    extra = 0                 # không sinh form trống
    fields = ('name',)        # chỉ hiện tên (có thể thêm các field khác)
    show_change_link = True   # có link vào form edit của từng student
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
class StudentPaymentAdminForm(forms.ModelForm):
    class Meta:
        model = StudentPayment
        fields = '__all__'
        widgets = {
            # HTML5 month-picker
            'month': forms.TextInput(attrs={'type': 'month'}),
        }
class StudentPaymentAdmin(admin.ModelAdmin):
    form = StudentPaymentAdminForm
    list_display  = ('student','month','tuition_fee','meal_price','amount_paid','remaining_balance')
    search_fields = ('student__name','month')   # ← tìm theo tên học sinh hoặc tháng
    list_filter   = ('month',)                  # filter thêm theo tháng nếu cần
    verbose_name  = "Công nợ học sinh"
    verbose_name_plural = "Công nợ học sinh"
    def save_model(self, request, obj, form, change):
        """
        Nếu đã có record cùng student+month khác pk này,
        thì cập nhật vào record đó thay vì tạo mới.
        """
        existing = StudentPayment.objects.filter(
            student=obj.student,
            month=obj.month
        ).exclude(pk=obj.pk).first()

        if existing:
            # Ghi đè các trường
            existing.tuition_fee    = obj.tuition_fee
            existing.meal_price     = obj.meal_price
            existing.amount_paid    = obj.amount_paid
            # gọi save của model để tính remaining_balance
            existing.save()
            self.message_user(request, f"✅ Đã cập nhật bản ghi {existing.id} thay vì tạo mới.", level=messages.SUCCESS)
        else:
            super().save_model(request, obj, form, change)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [StudentInline]  
    verbose_name = "Lớp học"
    verbose_name_plural = "Các lớp học"
    change_form_template = "admin/meals/classroom_change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<int:classroom_id>/delete_students/',
                self.admin_site.admin_view(self.delete_students_view),
                name='meals_classroom_delete_students'
            ),
            path(
                '<int:classroom_id>/export_students/',
                self.admin_site.admin_view(self.export_students_view),
                name='meals_classroom_export_students'
            ),
            path(
                '<int:classroom_id>/import_students/',
                self.admin_site.admin_view(self.import_students_view),
                name='meals_classroom_import_students'
            ),
        ]
        # Đặt custom URLs lên trước để không bị chặn bởi mặc định
        return custom + urls
    def delete_students_view(self, request, classroom_id):
        room = ClassRoom.objects.get(pk=classroom_id)
        if request.method == 'POST':
            # xóa tất cả sinh viên trong lớp, cascades luôn MealRecord & StudentPayment
            qs = Student.objects.filter(classroom=room)
            count, _ = qs.delete()
            self.message_user(request, f"Đã xóa {count} học sinh (và dữ liệu liên quan) của lớp {room.name}.")
            return HttpResponseRedirect(f'../../{classroom_id}/change/')

        context = {
            **self.admin_site.each_context(request),
            'opts':    self.model._meta,
            'original': room,
            'title':   f'Xác nhận xóa toàn bộ học sinh lớp “{room.name}”',
        }
        return TemplateResponse(request, "admin/meals/classroom_delete_students_confirmation.html", context)
    
    def export_students_view(self, request, classroom_id):
        room = ClassRoom.objects.get(pk=classroom_id)
        qs = Student.objects.filter(classroom=room).order_by('name')

        # Tạo workbook và sheet
        wb = Workbook()
        ws = wb.active
        ws.title = 'Học sinh'

        # Header
        ws.append(['Tên học sinh'])

        # Dữ liệu
        for s in qs:
            ws.append([s.name])

        # Xuất file .xlsx
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"students_{room.name}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response
    def import_students_view(self, request, classroom_id):
        room = ClassRoom.objects.get(pk=classroom_id)

        if request.method == 'POST':
            excel_file = request.FILES.get('excel_file')
            if not excel_file:
                self.message_user(request, "⚠️ Chưa chọn file Excel.", level=messages.ERROR)
                return HttpResponseRedirect(request.path)

            # Đọc workbook
            wb = load_workbook(filename=excel_file, read_only=True, data_only=True)
            ws = wb.active

            count = 0
            # Bắt đầu từ row 2 để bỏ header
            for row in ws.iter_rows(min_row=2, values_only=True):
                name = row[0]
                if name and str(name).strip():
                    Student.objects.get_or_create(name=str(name).strip(), classroom=room)
                    count += 1

            self.message_user(request, f"✅ Imported {count} học sinh vào lớp {room.name}.",
                               level=messages.SUCCESS)
            return HttpResponseRedirect(f'../../{classroom_id}/change/')

        # GET: render form
        context = {
            **self.admin_site.each_context(request),
            'opts':     self.model._meta,
            'original': room,
            'title':    f'Import học sinh cho lớp “{room.name}”',
        }
        return TemplateResponse(request, "admin/meals/import_students.html", context)

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
        existing_record = MealRecord.objects.filter(
             student=obj.student,
             date=obj.date,
             meal_type=obj.meal_type
         ).first()
        if existing_record:
            existing_record.status           = obj.status
            existing_record.non_eat          = obj.non_eat
            existing_record.absence_reason   = obj.absence_reason  # ← thêm dòng này
            existing_record.save()
        else:
             super().save_model(request, obj, form, change)
        
        # Xác định chuỗi "YYYY-MM" từ obj.date
        year_month = obj.date.strftime("%Y-%m")
        from .models import StudentPayment
        try:
            sp = StudentPayment.objects.get(student=obj.student, month=year_month)
            sp.save()  # gọi model.save() sẽ dùng meal_price để tính remaining_balance
        except StudentPayment.DoesNotExist:
            pass
        
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
try:
    my_admin_site.unregister(ClassRoom)
    my_admin_site.unregister(Student)
    my_admin_site.unregister(StudentPayment)
except:
    pass
my_admin_site.register(StudentPayment, StudentPaymentAdmin)
# đăng ký ClassRoomAdmin lên my_admin_site
my_admin_site.register(ClassRoom, ClassRoomAdmin)
my_admin_site.register(Student, StudentAdmin)
# Đăng ký thêm StudentPayment nếu muốn
my_admin_site.register(User, UserAdmin)
my_admin_site.register(Group, GroupAdmin)
my_admin_site.register(MealPrice, MealPriceAdmin)