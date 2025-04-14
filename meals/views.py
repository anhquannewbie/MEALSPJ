from django.shortcuts import render, get_object_or_404, redirect
from .models import MealRecord
from .forms import MealRecordForm
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import JsonResponse
from .models import Student
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta,datetime
from .models import MealRecord, Student
from .models import StudentPayment
from .forms import StudentPaymentForm,ClassRoom
from django.db import connection
import json
@csrf_exempt
def student_payment_edit(request, pk=None):
    classrooms = ClassRoom.objects.all()

    if request.method == "GET" and request.GET.get('payment_id'):
        try:
            payment = StudentPayment.objects.get(id=request.GET.get('payment_id'))
        except StudentPayment.DoesNotExist:
            payment = None
    else:
        if pk:
            payment = get_object_or_404(StudentPayment, pk=pk)
        else:
            payment = None

    if request.method == "POST":
        # Lấy dữ liệu từ form
        form = StudentPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            student = form.cleaned_data.get('student')
            month = form.cleaned_data.get('month')
            
            # Luôn kiểm tra xem có bản ghi tồn tại với student và month không
            # Bỏ điều kiện "not payment" để đảm bảo luôn kiểm tra và cập nhật
            existing_payment = StudentPayment.objects.filter(student=student, month=month).first()
            
            if existing_payment and (not payment or existing_payment.id != payment.id):
                # Nếu tìm thấy một bản ghi khác với bản ghi hiện tại
                # Cập nhật các giá trị từ form sang bản ghi đó
                existing_payment.tuition_fee = form.cleaned_data.get('tuition_fee')
                existing_payment.daily_meal_fee = form.cleaned_data.get('daily_meal_fee')
                existing_payment.amount_paid = form.cleaned_data.get('amount_paid')
                existing_payment.save()  # Cập nhật remaining_balance bằng phương thức save
                payment_obj = existing_payment
            else:
                # Nếu không tìm thấy hoặc đang chỉnh sửa bản ghi hiện tại
                payment_obj = form.save()
            with connection.cursor() as cursor:
                cursor.execute("""
                UPDATE meals_studentpayment
                SET remaining_balance = amount_paid - tuition_fee - (daily_meal_fee * 26)+ COALESCE((SELECT sp_prev.remaining_balance FROM meals_studentpayment AS sp_prev WHERE sp_prev.student_id = meals_studentpayment.student_id AND sp_prev.month = strftime('%Y-%m', date(meals_studentpayment.month || '-01', '-1 month')) ORDER BY sp_prev.id DESC LIMIT 1), 0);
                """)
            messages.success(request, "Lưu thành công")
            return redirect(request.path)
        else:
            print("Form errors:", form.errors)
    else:
        form = StudentPaymentForm(instance=payment)

    var_is_edit = True if payment and payment.pk else False
    return render(request, 'payments/student_payment_form.html', {
        'form': form,
        'classrooms': classrooms,
        'is_edit': var_is_edit,
    })

# Các view khác giữ nguyên
def ajax_load_students(request):
    classroom_id = request.GET.get('classroom_id')
    if classroom_id:
        students = Student.objects.filter(classroom_id=classroom_id).order_by('name')
        student_list = [{'id': s.id, 'name': s.name} for s in students]
    else:
        student_list = []
    return JsonResponse(student_list, safe=False)

def ajax_load_previous_balance(request):
    student_id = request.GET.get('student_id')
    month = request.GET.get('month')  # 'YYYY-MM'
    prior_balance = 0
    if student_id and month:
        from datetime import datetime, timedelta
        dt = datetime.strptime(month, '%Y-%m')
        prev_month = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        
        from .models import StudentPayment
        prev_payment = StudentPayment.objects.filter(student_id=student_id, month=prev_month).order_by('-id').first()
        if prev_payment:
            prior_balance = prev_payment.remaining_balance or 0
    return JsonResponse({'prev_month_balance': prior_balance})

def ajax_load_payment_details(request):
    student_id = request.GET.get('student_id')
    month = request.GET.get('month')  # format 'YYYY-MM'
    data = {}

    if student_id and month:
        # 1. Lấy payment của THÁNG HIỆN TẠI (nếu có) -> để load tuition_fee, daily_meal_fee, amount_paid, v.v.
        payment = StudentPayment.objects.filter(student_id=student_id, month=month).first()
        if payment:
            data['tuition_fee'] = str(payment.tuition_fee)
            data['daily_meal_fee'] = str(payment.daily_meal_fee)
            data['amount_paid'] = str(payment.amount_paid)
            # "Tiền tháng này" = remaining_balance
            data['current_month_payment'] = str(payment.remaining_balance)
        else:
            # Nếu chưa có payment cho tháng này => để trống
            data['tuition_fee'] = ''
            data['daily_meal_fee'] = ''
            data['amount_paid'] = ''
            data['current_month_payment'] = ''

        # 2. Tính "Tiền tháng trước" = remaining_balance của tháng trước (nếu có)
        dt = datetime.strptime(month, '%Y-%m')
        prev_month = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        prev_payment = StudentPayment.objects.filter(student_id=student_id, month=prev_month).first()
        if prev_payment:
            data['prev_month_balance'] = str(prev_payment.remaining_balance)
        else:
            data['prev_month_balance'] = '0'
    else:
        # Nếu thiếu student hoặc month -> mọi thứ để trống
        data['tuition_fee'] = ''
        data['daily_meal_fee'] = ''
        data['amount_paid'] = ''
        data['current_month_payment'] = ''
        data['prev_month_balance'] = '0'

    return JsonResponse(data)

def bulk_meal_record_save(request):
    if request.method == 'POST':
        class_name = request.POST.get('class_name')
        meal_type = request.POST.get('meal_type')
        student_ids = request.POST.getlist('student_ids[]')
        print("DEBUG: student_ids =", student_ids)  # Debug: in ra danh sách học sinh có tick
        today = date.today()

        absence_data_str = request.POST.get('absence_data', '{}')
        absence_data = json.loads(absence_data_str)
        print("DEBUG: absence_data =", absence_data)  # Debug: in ra dữ liệu dropdown

        students = Student.objects.filter(classroom__name=class_name)
        MealRecord.objects.filter(student__in=students, date=today, meal_type=meal_type).delete()

        for student in students:
            sid = str(student.id)
            if sid in student_ids:
                status = "Đủ"
                non_eat = 0
            else:
                status = "Thiếu"
                non_eat = int(absence_data.get(sid, "2"))
            print("DEBUG: For student", sid, "status =", status, "non_eat =", non_eat)
            MealRecord.objects.create(
                student=student,
                date=today,
                meal_type=meal_type,
                status=status,
                non_eat=non_eat
            )
            
        return JsonResponse({"message": "success"}, status=200)
    return JsonResponse({"error": "Invalid method"}, status=400)

def bulk_meal_record_create(request):
    # Lấy danh sách lớp (distinct)
    class_list = Student.objects.values_list('classroom__name', flat=True).distinct()

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

def load_students(request):
    # Ajax view: Lấy danh sách học sinh dựa theo lớp học đã chọn
    class_name = request.GET.get('class_name')
    students = []
    if class_name:
        students = Student.objects.filter(classroom__name=class_name).order_by('name')
    data = [{'id': student.id, 'name': student.name} for student in students]
    return JsonResponse(data, safe=False)