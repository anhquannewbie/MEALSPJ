from django.shortcuts import render, get_object_or_404, redirect
from .models import MealRecord
from .forms import MealRecordForm
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import JsonResponse
from .models import Student
from django.views.decorators.csrf import csrf_exempt
from datetime import date
from .models import MealRecord, Student
@csrf_exempt
def bulk_meal_record_save(request):
    if request.method == 'POST':
        class_name = request.POST.get('class_name')
        meal_type = request.POST.get('meal_type')
        # Lấy danh sách các giá trị từ checkbox
        student_ids = request.POST.getlist('student_ids[]') 
        today = date.today()

        # Lấy tất cả học sinh của lớp đó
        students = Student.objects.filter(class_name=class_name)

        # Xóa các bản ghi cũ của lớp, meal_type trong ngày hôm nay
        MealRecord.objects.filter(student__in=students, date=today, meal_type=meal_type).delete()

        # Tạo bản ghi mới cho tất cả học sinh trong lớp:
        # Nếu học sinh được chọn (checkbox tick) thì lưu "Đủ", ngược lại lưu "Thiếu".

        for student in students:
            status = "Đủ" if str(student.id) in student_ids else "Thiếu"
            MealRecord.objects.create(
                student=student,
                date=today,
                meal_type=meal_type,
                status=status
            )
            
        return JsonResponse({"message": "success"}, status=200)

    return JsonResponse({"error": "Invalid method"}, status=400)

def bulk_meal_record_create(request):
    # Lấy danh sách lớp (distinct)
    class_list = Student.objects.values_list('class_name', flat=True).distinct()

    return render(request, 'meals/bulk_meal_form.html', {
        'class_list': class_list,
        'title': 'Nhập Dữ liệu Bữa Ăn'
    })
def meal_record_list(request):
    records = MealRecord.objects.all().order_by('-date')
    return render(request, 'meals/meal_list.html', {'records': records, 'title': _("Danh sách Bữa Ăn")})

def meal_record_detail(request, pk):
    record = get_object_or_404(MealRecord, pk=pk)
    return render(request, 'meals/meal_detail.html', {'record': record, 'title': _("Chi tiết Bữa Ăn")})

# def meal_record_create(request):
#     if request.method == 'POST':
#         form = MealRecordForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, _("Bản ghi bữa ăn đã được lưu thành công!"))
#             return redirect('meals:meal_list')
#     else:
#         form = MealRecordForm()
#     return render(request, 'meals/meal_form.html', {'form': form, 'title': _("Nhập Dữ liệu Bữa Ăn")})

def load_students(request):
    # Ajax view: Lấy danh sách học sinh dựa theo lớp học đã chọn
    class_name = request.GET.get('class_name')
    students = []
    if class_name:
        students = Student.objects.filter(class_name=class_name).order_by('name')
    data = [{'id': student.id, 'name': student.name} for student in students]
    return JsonResponse(data, safe=False)
