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
from django.db.models import Q
import calendar
import openpyxl
from django.http import HttpResponse
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
        form = StudentPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            student = form.cleaned_data.get('student')
            month = form.cleaned_data.get('month')
            # Luôn kiểm tra xem có bản ghi tồn tại với student và month không
            existing_payment = StudentPayment.objects.filter(student=student, month=month).first()
            if existing_payment and (not payment or existing_payment.id != payment.id):
                existing_payment.tuition_fee = form.cleaned_data.get('tuition_fee')
                existing_payment.daily_meal_fee = form.cleaned_data.get('daily_meal_fee')
                existing_payment.amount_paid = form.cleaned_data.get('amount_paid')
                existing_payment.save()
                payment_obj = existing_payment
            else:
                payment_obj = form.save()
            with connection.cursor() as cursor:
                cursor.execute("""
                UPDATE meals_studentpayment
                SET remaining_balance = amount_paid - tuition_fee - (daily_meal_fee * 26)+ COALESCE(
                    (SELECT sp_prev.remaining_balance 
                     FROM meals_studentpayment AS sp_prev 
                     WHERE sp_prev.student_id = meals_studentpayment.student_id 
                       AND sp_prev.month = strftime('%Y-%m', date(meals_studentpayment.month || '-01', '-1 month'))
                     ORDER BY sp_prev.id DESC LIMIT 1), 0);
                """)
            messages.success(request, "Lưu thành công")
            return redirect(request.path)
        else:
            print("Form errors:", form.errors)
    else:
        form = StudentPaymentForm(instance=payment)
    
    # Nếu có instance và có học sinh & month, đếm số bữa ăn (chỉ cho bữa sáng và bữa trưa)
    breakfast_count = 0
    lunch_count = 0
    if form.instance and form.instance.pk and form.instance.student and form.instance.month:
        try:
            year_str, month_str = form.instance.month.split("-")
            year = int(year_str)
            month_val = int(month_str)
            breakfast_count = MealRecord.objects.filter(
                student=form.instance.student,
                date__year=year,
                date__month=month_val,
                meal_type="Bữa sáng"
            ).filter(
                Q(status="Đủ") | Q(status="Thiếu", non_eat=2)
            ).count()
            lunch_count = MealRecord.objects.filter(
                student=form.instance.student,
                date__year=year,
                date__month=month_val,
                meal_type="Bữa trưa"
            ).filter(
                Q(status="Đủ") | Q(status="Thiếu", non_eat=2)
            ).count()
        except Exception as e:
            print("Error counting meals:", e)
    
    var_is_edit = True if payment and payment.pk else False
    return render(request, 'payments/student_payment_form.html', {
        'form': form,
        'classrooms': classrooms,
        'is_edit': var_is_edit,
        'breakfast_count': breakfast_count,
        'lunch_count': lunch_count,
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
        # 1. Lấy payment của THÁNG HIỆN TẠI (nếu có)
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

        # 2. Tính "Tiền tháng trước"
        from datetime import datetime, timedelta
        dt = datetime.strptime(month, '%Y-%m')
        prev_month = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        prev_payment = StudentPayment.objects.filter(student_id=student_id, month=prev_month).first()
        if prev_payment:
            data['prev_month_balance'] = str(prev_payment.remaining_balance)
        else:
            data['prev_month_balance'] = '0'

        # 3. Tính số bữa sáng và bữa trưa (breakfast_count, lunch_count)
        # Lấy year, month từ tham số
        year_val = dt.year
        month_val = dt.month

        breakfast_count = 0
        lunch_count = 0

        # Lấy các MealRecord của học sinh trong year_val, month_val
        from django.db.models import Q
        meal_records = MealRecord.objects.filter(
            student_id=student_id,
            date__year=year_val,
            date__month=month_val
        )
        # Duyệt qua meal_records, đếm bữa sáng và trưa nếu status="Đủ" hoặc (status="Thiếu" và non_eat=2)
        for r in meal_records:
            if (r.status == "Đủ") or (r.status == "Thiếu" and r.non_eat == 2):
                if r.meal_type == "Bữa sáng":
                    breakfast_count += 1
                elif r.meal_type == "Bữa trưa":
                    lunch_count += 1

        data['breakfast_count'] = breakfast_count
        data['lunch_count'] = lunch_count

    else:
        # Nếu thiếu student hoặc month -> mọi thứ để trống
        data['tuition_fee'] = ''
        data['daily_meal_fee'] = ''
        data['amount_paid'] = ''
        data['current_month_payment'] = ''
        data['prev_month_balance'] = '0'
        data['breakfast_count'] = 0
        data['lunch_count'] = 0

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
            current_month = today.strftime("%Y-%m")
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("UPDATE meals_studentpayment SET remaining_balance = amount_paid - tuition_fee - (SELECT COALESCE(SUM(CASE WHEN meal_type = 'Bữa sáng' AND (status = 'Đủ' OR (status = 'Thiếu' AND non_eat = 2)) THEN 10000 WHEN meal_type = 'Bữa trưa' AND (status = 'Đủ' OR (status = 'Thiếu' AND non_eat = 2)) THEN CASE WHEN meals_studentpayment.daily_meal_fee = 30000 THEN 20000 WHEN meals_studentpayment.daily_meal_fee = 40000 THEN 30000 ELSE meals_studentpayment.daily_meal_fee - 10000 END ELSE 0 END), 0) FROM meals_mealrecord WHERE meals_mealrecord.student_id = meals_studentpayment.student_id AND strftime('%%Y-%%m', meals_mealrecord.date) = meals_studentpayment.month) + COALESCE((SELECT sp_prev.remaining_balance FROM meals_studentpayment AS sp_prev WHERE sp_prev.student_id = meals_studentpayment.student_id AND sp_prev.month = strftime('%%Y-%%m', date(meals_studentpayment.month || '-01', '-1 month')) ORDER BY sp_prev.id DESC LIMIT 1), 0) WHERE month = %s AND student_id IN (SELECT id FROM meals_student WHERE classroom_id = (SELECT id FROM meals_classroom WHERE name = %s));", [current_month, class_name])
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
def ajax_load_mealdata(request):
    """
    Endpoint trả về danh sách học sinh của lớp được chọn, kèm thông tin MealRecord của ngày hôm qua cho loại bữa ăn được chọn.
    Nếu có MealRecord: trả về dữ liệu record (checkbox checked nếu status="Đủ", không tick nếu status="Thiếu" và trả về non_eat).
    Nếu không có MealRecord: mặc định checkbox tick, non_eat mặc định là 1 (Có phép).
    """
    class_name = request.GET.get('class_name')
    meal_type = request.GET.get('meal_type')  # ví dụ: "Bữa sáng" hoặc "Bữa trưa"
    
    # Ngày hôm qua
    yesterday = date.today() - timedelta(days=1)
    
    # Lấy danh sách học sinh của lớp
    students = Student.objects.filter(classroom__name=class_name).order_by('name')
    
    data = []
    for student in students:
        # Tìm MealRecord của học sinh cho ngày hôm qua và meal_type
        record = MealRecord.objects.filter(student=student, date=yesterday, meal_type=meal_type).first()
        if record:
            # Nếu có bản ghi, set checkbox theo status
            item = {
                'id': student.id,
                'name': student.name,
                # Nếu record.status=="Đủ" thì checkbox tick; nếu "Thiếu" thì không tick.
                'checked': True if record.status == "Đủ" else False,
                'non_eat': record.non_eat  # Giá trị của non_eat từ record (1 hoặc 2)
            }
        else:
            # Nếu không có bản ghi thì mặc định:
            item = {
                'id': student.id,
                'name': student.name,
                'checked': True,  # tick mặc định (ăn đủ)
                'non_eat': 1      # mặc định "Có phép" (nhưng nếu tick thì dropdown sẽ bị disable)
            }
        data.append(item)
    return JsonResponse(data, safe=False)
def statistics_view(request):
    # 1. Lấy danh sách lớp (ClassRoom)
    classrooms = ClassRoom.objects.all().order_by('name')
    
    # 2. Lấy danh sách năm (distinct) từ field date trong MealRecord
    #    Ví dụ: [2023, 2024, 2025]
    meal_dates = MealRecord.objects.values_list('date', flat=True)
    years_set = set([d.year for d in meal_dates])
    years_list = sorted(list(years_set))

    # 3. Lấy các tham số từ request GET (hoặc POST) để lọc
    selected_year = request.GET.get('year')  # vd: '2025'
    selected_month = request.GET.get('month')  # vd: '03'
    selected_meal_type = request.GET.get('meal_type')  # vd: 'Bữa sáng'
    selected_class_id = request.GET.get('class_id')  # id lớp
    mode = request.GET.get('mode', 'month')  # 'month' hoặc 'year' tùy tab

    # Tạo biến context để render ra template
    context = {
        'classrooms': classrooms,
        'years_list': years_list,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_meal_type': selected_meal_type,
        'selected_class_id': selected_class_id,
        'mode': mode,
    }

    # 4. Nếu người dùng đã chọn year => Lấy các tháng (distinct) trong MealRecord tương ứng
    #    Tương tự, ta trích ra list tháng (1..12) có dữ liệu.
    if selected_year:
        # Lọc MealRecord theo year
        year_meals = MealRecord.objects.filter(date__year=int(selected_year))
        # Rút ra các tháng distinct
        months_set = set(m.date.month for m in year_meals)
        months_list = sorted(list(months_set))
    else:
        months_list = []

    context['months_list'] = months_list

    # 5. Phần "Thống kê theo tháng"
    #    - Nếu người dùng chọn year, month, meal_type, class_id => Tạo bảng 31 cột
    #    - Mỗi học sinh 1 hàng
    #    - Từng ô: X, P, KP, 0
    if mode == 'month':
        if selected_year and selected_month and selected_meal_type and selected_class_id:
            try:
                class_id_int = int(selected_class_id)
            except:
                class_id_int = None
            
            students = Student.objects.filter(classroom_id=class_id_int).order_by('name')
            max_day = calendar.monthrange(int(selected_year), int(selected_month))[1]  # Số ngày của tháng

            # Lấy MealRecord cho tất cả học sinh trong lớp, cho đúng meal_type
            year_i = int(selected_year)
            month_i = int(selected_month)
            records = MealRecord.objects.filter(
                student__classroom_id=class_id_int,
                meal_type=selected_meal_type,
                date__year=year_i,
                date__month=month_i
            )

            # Tạo dict { (stu_id, day) : (status, non_eat) } để tra nhanh
            record_map = {}
            for rec in records:
                record_map[(rec.student_id, rec.date.day)] = (rec.status, rec.non_eat)

            rows_data = []
            for stu in students:
                # NEW: Chuẩn bị tính tổng bữa ăn và tổng tiền
                total_meals = 0
                total_cost = 0

                # NEW: Truy vấn lấy daily_meal_fee từ StudentPayment (nếu có)
                #     (Giả sử mỗi học sinh chỉ có 1 StudentPayment cho month này)
                #     Nếu có nhiều thì bạn cần tùy biến thêm.
                year_month_str = f"{selected_year}-{selected_month.zfill(2)}"
                sp = StudentPayment.objects.filter(student=stu, month=year_month_str).first()
                daily_meal_fee=0
                if sp:
                    daily_meal_fee = float(sp.daily_meal_fee)
                else:
                    # Nếu không có studentPayment, có thể đặt default = 30
                    daily_meal_fee = 30000
                print(daily_meal_fee)
                fee_breakfast = 10
                # bữa trưa = daily_meal_fee - 10, trừ các case 30 -> 20, 40 -> 30
                if daily_meal_fee == 30000:
                    fee_lunch = 20000
                elif daily_meal_fee == 40000:
                    fee_lunch = 30000
                else:
                    fee_lunch = daily_meal_fee - 10000

                days_array = []
                for d in range(1, 32):  # 1..31 cột
                    if d > max_day:
                        # nếu d vượt số ngày thật -> hiển thị '0'
                        days_array.append('0')
                    else:
                        status_tuple = record_map.get((stu.id, d))  # (status, non_eat)
                        if status_tuple:
                            s, n_eat = status_tuple
                            if s == 'Đủ':
                                days_array.append('X')
                                # NEW: tính tổng
                                total_meals += 1
                                # NEW: cộng tiền
                                if selected_meal_type == 'Bữa sáng':
                                    total_cost += fee_breakfast
                                else:
                                    total_cost += fee_lunch
                            elif s == 'Thiếu':
                                if n_eat == 1:
                                    days_array.append('P')  # Có phép
                                elif n_eat == 2:
                                    days_array.append('KP')  # Không phép
                                    # NEW: vẫn tính
                                    total_meals += 1
                                    if selected_meal_type == 'Bữa sáng':
                                        total_cost += fee_breakfast
                                    else:
                                        total_cost += fee_lunch
                            else:
                                days_array.append('0')
                        else:
                            days_array.append('0')
                
                row = {
                    'student': stu,
                    'days': days_array,
                    'total_meals': total_meals,  # NEW
                    'total_cost': total_cost,    # NEW
                }
                rows_data.append(row)
            
            context['rows_data'] = rows_data
            context['max_day'] = 31  # hiển thị đủ 31 cột

    # 6. Phần "Thống kê theo năm"
    #    - Nếu mode='year' => người dùng chọn year, meal_type, class_id => hiển thị bảng cột 12 tháng
    if mode == 'year':
        if selected_year and selected_meal_type and selected_class_id:
            class_id_int = int(selected_class_id)
            students = Student.objects.filter(classroom_id=class_id_int).order_by('name')

            # Tạo cột 12 tháng => cho each student => đếm tổng record
            # logic: count number of records with meal_type=..., status=..., non_eat=...
            # Hoặc: sum all (dù Đủ hay Thiếu) => user tuỳ chọn
            # Ở đây, ví dụ: ta đếm TẤT CẢ MealRecord (status='Đủ' or 'Thiếu') => user tuỳ
            year_i = int(selected_year)
            monthly_count = {}
            for stu in students:
                monthly_count[stu.id] = {}
                for m in range(1, 13):
                    monthly_count[stu.id][m] = 0
            
            # Lấy MealRecord
            recs_year = MealRecord.objects.filter(
                student__classroom_id=class_id_int,
                date__year=year_i,
                meal_type=selected_meal_type
            )
            # Đếm
            for r in recs_year:
                mm = r.date.month
                monthly_count[r.student.id][mm] += 1  # sum record (bạn có thể tuỳ chọn logic)
            
            rows_year = []
            for stu in students:
                row = {
                    'student': stu,
                    'months': [monthly_count[stu.id][m] for m in range(1, 13)]
                }
                rows_year.append(row)
            
            context['rows_year'] = rows_year

    return render(request, 'meals/statistics.html', context)
def ajax_load_months(request):
    year = request.GET.get('year')
    # Lọc MealRecord date__year=year
    year_meals = MealRecord.objects.filter(date__year=int(year))
    months_set = {m.date.month for m in year_meals}
    months_list = sorted(list(months_set))
    return JsonResponse(months_list, safe=False)
import calendar
import openpyxl
from django.http import HttpResponse
from .models import Student, MealRecord, StudentPayment, ClassRoom

def export_monthly_statistics(request):
    selected_year      = request.GET.get('year')
    selected_month     = request.GET.get('month')
    selected_meal_type = request.GET.get('meal_type')
    selected_class_id  = request.GET.get('class_id')
    
    if not (selected_year and selected_month and selected_meal_type and selected_class_id):
        return HttpResponse("Thiếu tham số", status=400)
    
    # Chuyển kiểu và tính số ngày
    year_i  = int(selected_year)
    month_i = int(selected_month)
    max_day = calendar.monthrange(year_i, month_i)[1]
    
    # Lấy lớp và danh sách học sinh
    try:
        class_id_int = int(selected_class_id)
        classroom    = ClassRoom.objects.get(id=class_id_int)
    except Exception:
        return HttpResponse("Lớp học không hợp lệ", status=400)
    students = Student.objects.filter(classroom=classroom).order_by('name')
    
    # Lấy các MealRecord trong tháng
    records = MealRecord.objects.filter(
        student__classroom=classroom,
        meal_type=selected_meal_type,
        date__year=year_i,
        date__month=month_i
    )
    record_map = {
        (r.student_id, r.date.day): (r.status, r.non_eat)
        for r in records
    }
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"TK {selected_month}-{selected_year}"
    
    # --- 1. Big Title (merge A1 → (3+max_day)2) ---
    last_col = 3 + max_day  # cột cuối cùng: A=1, ngày từ 2→(1+max_day), Tổng=(2+max_day), Thành tiền=(3+max_day)
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=last_col)
    title = f"BẢNG CHẤM {selected_meal_type.upper()} THÁNG {selected_month}/{selected_year} - LỚP: {classroom.name}"
    cell = ws.cell(row=1, column=1, value=title)
    cell.alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center')
    cell.font      = openpyxl.styles.Font(size=14, bold=True)
    
    # --- 2. Header cột (row 3) ---
    headers = ["Học sinh"] + [str(d) for d in range(1, max_day+1)] + ["Tổng", "Thành tiền"]
    for idx, h in enumerate(headers, start=1):
        c = ws.cell(row=3, column=idx, value=h)
        c.font      = openpyxl.styles.Font(bold=True)
        c.alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center')
        # Giãn độ rộng cột
        ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = 12 if idx <= 2 else 5
    
    # --- 3. Thêm dữ liệu học sinh (bắt đầu row 4) ---
    row_num = 4
    for stu in students:
        # Lấy daily_meal_fee của học sinh
        ym_str = f"{selected_year}-{selected_month.zfill(2)}"
        sp = StudentPayment.objects.filter(student=stu, month=ym_str).first()
        daily_fee = float(sp.daily_meal_fee) if sp else 30000.0
        
        # Tính phí sáng/trưa (nghìn đồng)
        fee_break = 10000
        if daily_fee == 30000:
            fee_lunch = 20000
        elif daily_fee == 40000:
            fee_lunch = 30000
        else:
            fee_lunch = daily_fee - 10000
        
        total_meals = 0
        total_cost  = 0
        row = [stu.name]
        
        # Chấm từng ngày
        for d in range(1, max_day+1):
            status = record_map.get((stu.id, d))
            if status:
                s, ne = status
                if s == "Đủ" or (s == "Thiếu" and ne == 2):
                    mark = "X"
                    total_meals += 1
                    total_cost  += (fee_break if selected_meal_type=="Bữa sáng" else fee_lunch)
                elif s == "Thiếu" and ne == 1:
                    mark = "P"
                else:
                    mark = "0"
            else:
                mark = "0"
            row.append(mark)
        
        # Nếu bạn muốn luôn xuất 31 ngày bất kể max_day, uncomment đoạn sau:
        # for d in range(max_day+1, 32):
        #     row.append("0")
        
        # Tổng và Thành tiền
        row += [total_meals, total_cost]
        
        # Ghi vào sheet
        for idx, val in enumerate(row, start=1):
            ws.cell(row=row_num, column=idx, value=val)
        row_num += 1
    
    # --- 4. Trả file ---
    resp = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    fname = f"ThongKe_{selected_year}_{selected_month}.xlsx"
    resp["Content-Disposition"] = f'attachment; filename="{fname}"'
    wb.save(resp)
    return resp
