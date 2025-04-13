from django.shortcuts import render, get_object_or_404, redirect
from .models import MealRecord
from .forms import MealRecordForm
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import JsonResponse
from .models import Student
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta
from .models import MealRecord, Student
from .models import StudentPayment
from .forms import StudentPaymentForm,ClassRoom
@csrf_exempt
def student_payment_edit(request, pk=None):
    # Lấy danh sách lớp có sẵn
    classrooms = ClassRoom.objects.all()

    # Nếu có truyền pk (sửa thông tin thanh toán), dùng instance hiện có
    if pk:
        payment = get_object_or_404(StudentPayment, pk=pk)
    else:
        payment = None

    if request.method == "POST":
        # Sử dụng form nhập liệu (không bao gồm trường học sinh vì học sinh sẽ được chọn qua AJAX)
        form = StudentPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment_obj = form.save()  # Phương thức save() sẽ tự tính toán remaining_balance
            return redirect('payment_list')  # Điều hướng sang trang danh sách thanh toán
    else:
        form = StudentPaymentForm(instance=payment)

    return render(request, 'payments/student_payment_form.html', {
        'form': form,
        'classrooms': classrooms
    })

# View AJAX: Khi chọn lớp, trả về danh sách học sinh của lớp đó
def ajax_load_students(request):
    classroom_id = request.GET.get('classroom_id')
    if classroom_id:
        students = Student.objects.filter(classroom_id=classroom_id).order_by('name')
        student_list = [{'id': s.id, 'name': s.name} for s in students]
    else:
        student_list = []
    return JsonResponse(student_list, safe=False)

# View AJAX: Khi chọn học sinh, load số dư (previous_balance) của tháng trước, nếu có.
# Giả sử tháng trước = tháng hiện tại - 1 tháng theo format 'YYYY-MM'
def ajax_load_previous_balance(request):
    student_id = request.GET.get('student_id')
    month = request.GET.get('month')  # ở format 'YYYY-MM'
    # Tính tháng trước: chuyển đổi sang datetime sau đó trừ 1 tháng
    if month and student_id:
        dt = datetime.strptime(month, '%Y-%m')
        # Giả sử cách tính: nếu tháng là 2025-04 thì tháng trước là 2025-03
        # Truy vấn StudentPayment với student và month bằng tháng trước
        previous_month = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        prev_payment = StudentPayment.objects.filter(student_id=student_id, month=previous_month).order_by('-id').first()
        previous_balance = prev_payment.remaining_balance if prev_payment else 0
    else:
        previous_balance = 0
    return JsonResponse({'previous_balance': previous_balance})
def bulk_meal_record_save(request):
    if request.method == 'POST':
        class_name = request.POST.get('class_name')
        meal_type = request.POST.get('meal_type')
        # Lấy danh sách các giá trị từ checkbox
        student_ids = request.POST.getlist('student_ids[]') 
        today = date.today()

        # Lấy tất cả học sinh của lớp đó
        students = Student.objects.filter(classroom_name=class_name)

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
    class_list = Student.objects.values_list('classroom_name', flat=True).distinct()

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
