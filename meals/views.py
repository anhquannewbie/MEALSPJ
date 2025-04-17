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
from openpyxl.styles import Alignment, Font
from decimal import Decimal
from openpyxl.utils import get_column_letter
@csrf_exempt
def student_payment_edit(request, pk=None):
    classrooms = ClassRoom.objects.all()

    # Lấy bản ghi nếu edit
    if request.method == "GET" and request.GET.get('payment_id'):
        try:
            payment = StudentPayment.objects.get(id=request.GET.get('payment_id'))
        except StudentPayment.DoesNotExist:
            payment = None
    else:
        payment = get_object_or_404(StudentPayment, pk=pk) if pk else None

    if request.method == "POST":
        form = StudentPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            student = form.cleaned_data['student']
            month   = form.cleaned_data['month']

            # Kiểm tra duplicate
            existing = StudentPayment.objects.filter(student=student, month=month).first()
            if existing and (not payment or existing.id != payment.id):
                # Cập nhật bản ghi tồn tại
                existing.tuition_fee    = form.cleaned_data['tuition_fee']
                existing.daily_meal_fee = form.cleaned_data['daily_meal_fee']
                existing.amount_paid    = form.cleaned_data['amount_paid']
                existing.save()     # <-- gọi vào StudentPayment.save(), sẽ tính đúng remaining_balance
                payment_obj = existing
            else:
                # Tạo mới hoặc cập nhật chính nó
                payment_obj = form.save()  # <-- gọi vào StudentPayment.save()

            messages.success(request, "Lưu thành công")
            return redirect(request.path)
        else:
            print("Form errors:", form.errors)
    else:
        form = StudentPaymentForm(instance=payment)

    # Tính số bữa sáng/trưa để hiện lên form
    breakfast_count = lunch_count = 0
    if form.instance and form.instance.pk and form.instance.student and form.instance.month:
        try:
            y, m = map(int, form.instance.month.split("-"))
            qs = MealRecord.objects.filter(
                student=form.instance.student,
                date__year=y, date__month=m,
                meal_type__in=["Bữa sáng","Bữa trưa"]
            ).filter(Q(status="Đủ")|Q(status="Thiếu", non_eat=2))
            breakfast_count = qs.filter(meal_type="Bữa sáng").count()
            lunch_count     = qs.filter(meal_type="Bữa trưa").count()
        except Exception as e:
            print("Error counting meals:", e)

    var_is_edit = bool(payment and payment.pk)
    return render(request, 'payments/student_payment_form.html', {
        'form': form,
        'classrooms':    classrooms,
        'is_edit':       var_is_edit,
        'breakfast_count': breakfast_count,
        'lunch_count':     lunch_count,
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
    meal_dates = MealRecord.objects.values_list('date', flat=True)
    years_set = set(d.year for d in meal_dates)
    years_list = sorted(years_set)

    # 3. Lấy tham số từ request
    selected_year      = request.GET.get('year')
    selected_month     = request.GET.get('month')
    selected_meal_type = request.GET.get('meal_type')
    selected_class_id  = request.GET.get('class_id')
    mode               = request.GET.get('mode', 'month')

    context = {
        'classrooms':       classrooms,
        'years_list':       years_list,
        'selected_year':    selected_year,
        'selected_month':   selected_month,
        'selected_meal_type': selected_meal_type,
        'selected_class_id':  selected_class_id,
        'mode':             mode,
    }

    # Build danh sách tháng nếu đã chọn year
    if selected_year:
        year_meals = MealRecord.objects.filter(date__year=int(selected_year))
        months_set = set(m.date.month for m in year_meals)
        context['months_list'] = sorted(months_set)
    else:
        context['months_list'] = []

    # --- Thống kê theo tháng ---
    if mode == 'month' and selected_year and selected_month and selected_meal_type and selected_class_id:
        class_id_int = int(selected_class_id)
        students = Student.objects.filter(classroom_id=class_id_int).order_by('name')
        year_i = int(selected_year)
        month_i = int(selected_month)
        max_day = calendar.monthrange(year_i, month_i)[1]

        # Lấy record và map lại
        recs = MealRecord.objects.filter(
            student__classroom_id=class_id_int,
            meal_type=selected_meal_type,
            date__year=year_i,
            date__month=month_i
        )
        record_map = {
            (r.student_id, r.date.day): (r.status, r.non_eat)
            for r in recs
        }

        # Tạo rows_data
        rows_data = []
        for stu in students:
            # Lấy daily_fee từ StudentPayment (nếu có)
            ym = f"{selected_year}-{selected_month.zfill(2)}"
            sp = StudentPayment.objects.filter(student=stu, month=ym).first()
            daily_fee = float(sp.daily_meal_fee) if sp else 30000.0
            fee_break = 10000
            fee_lunch = (
                20000 if daily_fee == 30000 else
                30000 if daily_fee == 40000 else
                daily_fee - 10000
            )

            days_array = []
            total_meals = 0
            total_cost  = 0
            for d in range(1, 32):
                if d > max_day:
                    days_array.append('0')
                else:
                    val = record_map.get((stu.id, d))
                    if val:
                        s, ne = val
                        if s == 'Đủ':
                            days_array.append('X')
                            total_meals += 1
                            total_cost  += (fee_break if selected_meal_type=='Bữa sáng' else fee_lunch)
                        elif s == 'Thiếu' and ne == 1:
                            days_array.append('P')
                        elif s == 'Thiếu' and ne == 2:
                            days_array.append('KP')
                            total_meals += 1
                            total_cost  += (fee_break if selected_meal_type=='Bữa sáng' else fee_lunch)
                        else:
                            days_array.append('0')
                    else:
                        days_array.append('0')
            rows_data.append({
                'student':     stu,
                'days':        days_array,
                'total_meals': total_meals,
                'total_cost':  total_cost,
            })

        # Tính totals_per_day
        totals_per_day = []
        for idx in range(31):
            if idx+1 > max_day:
                totals_per_day.append(0)
            else:
                cnt = sum(1 for row in rows_data if row['days'][idx] in ('X','KP'))
                totals_per_day.append(cnt)

        context.update({
            'rows_data':        rows_data,
            'max_day':          31,
            'totals_per_day':   totals_per_day,
        })

    # --- Thống kê theo năm ---
    if mode == 'year' and selected_year and selected_class_id:
        class_id_int = int(selected_class_id)
        classroom = get_object_or_404(ClassRoom, id=class_id_int)
        students = Student.objects.filter(classroom=classroom).order_by('name')
        year_i = int(selected_year)

        months = list(range(1, 13))
        rows_year = []
        totals_year_data = [ [Decimal('0'), Decimal('0'), Decimal('0')] for _ in months ]

        for stu in students:
            data_per_month = []
            for idx, m in enumerate(months):
                ym = f"{selected_year}-{m:02d}"
                sp = StudentPayment.objects.filter(student=stu, month=ym).first()

                # paid
                paid = sp.amount_paid if sp else Decimal('0')
                # tuition_fee
                tuition = sp.tuition_fee if sp else Decimal('0')
                # remaining_balance
                remaining = sp.remaining_balance if (sp and sp.remaining_balance is not None) else Decimal('0')

                # tính spent = tuition_fee + tiền ăn
                # Lấy meal records
                recs = MealRecord.objects.filter(
                    student=stu,
                    date__year=year_i,
                    date__month=m,
                    meal_type__in=["Bữa sáng","Bữa trưa"]
                )
                spent_meals = Decimal('0')
                # xác định phí trưa
                if sp:
                    df = sp.daily_meal_fee
                    if df == Decimal('30000'):
                        fee_lunch = Decimal('20000')
                    elif df == Decimal('40000'):
                        fee_lunch = Decimal('30000')
                    else:
                        fee_lunch = df - Decimal('10000')
                else:
                    fee_lunch = Decimal('20000')
                fee_break = Decimal('10000')

                for r in recs:
                    if r.status == 'Đủ' or (r.status=='Thiếu' and r.non_eat==2):
                        spent_meals += fee_break if r.meal_type=="Bữa sáng" else fee_lunch

                spent = tuition + spent_meals

                # cộng tổng lớp
                totals_year_data[idx][0] += paid
                totals_year_data[idx][1] += spent
                totals_year_data[idx][2] += remaining

                data_per_month.append({
                    'paid':      paid,
                    'spent':     spent,
                    'remaining': remaining,
                })

            rows_year.append({'student': stu, 'data': data_per_month})

        context.update({
            'mode':              'year',
            'months':            months,
            'rows_year':         rows_year,
            'totals_year_data':  totals_year_data,
        })

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
    except:
        return HttpResponse("Lớp học không hợp lệ", status=400)
    students = Student.objects.filter(classroom=classroom).order_by('name')
    
    # Lấy các MealRecord trong tháng
    recs = MealRecord.objects.filter(
        student__classroom=classroom,
        meal_type=selected_meal_type,
        date__year=year_i,
        date__month=month_i
    )
    # Map (student_id, day) -> (status, non_eat)
    record_map = {
        (r.student_id, r.date.day): (r.status, r.non_eat)
        for r in recs
    }
    
    # Tạo workbook và sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"TK {selected_month}-{selected_year}"
    
    # 1. Tiêu đề merge A1→(3+max_day)2
    last_col = 3 + max_day
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=last_col)
    title = f"BẢNG CHẤM {selected_meal_type.upper()} THÁNG {selected_month}/{selected_year} - LỚP: {classroom.name}"
    cell = ws.cell(row=1, column=1, value=title)
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.font      = Font(size=14, bold=True)
    
    # 2. Header cột (dòng 3)
    headers = ["Học sinh"] + [str(d) for d in range(1, max_day+1)] + ["Tổng", "Thành tiền"]
    for idx, h in enumerate(headers, start=1):
        c = ws.cell(row=3, column=idx, value=h)
        c.font      = Font(bold=True)
        c.alignment = Alignment(horizontal='center', vertical='center')
        ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = (12 if idx<=2 else 5)
    
    # 3. Dòng dữ liệu học sinh (bắt đầu từ row 4)
    row_num = 4
    # Dùng để tính hàng tổng sau này
    totals_per_day = [0] * max_day
    
    for stu in students:
        # Lấy daily_fee của học sinh
        ym_str = f"{selected_year}-{selected_month.zfill(2)}"
        sp = StudentPayment.objects.filter(student=stu, month=ym_str).first()
        daily_fee = float(sp.daily_meal_fee) if sp else 30000.0
        
        # Tính phí sáng/trưa
        fee_break = 10000
        fee_lunch = 20000 if daily_fee==30000 else 30000 if daily_fee==40000 else daily_fee - 10000
        
        total_meals = 0
        total_cost  = 0
        row = [stu.name]
        
        # Chấm từng ngày
        for d in range(1, max_day+1):
            status = record_map.get((stu.id, d))
            if status:
                s, ne = status
                if s == "Đủ" or (s=="Thiếu" and ne==2):
                    mark = "X"
                    total_meals += 1
                    total_cost  += (fee_break if selected_meal_type=="Bữa sáng" else fee_lunch)
                    totals_per_day[d-1] += 1
                elif s=="Thiếu" and ne==1:
                    mark = "P"
                else:
                    mark = "0"
            else:
                mark = "0"
            row.append(mark)
        
        # Thêm cột Tổng & Thành tiền
        row += [total_meals, total_cost]
        
        # Ghi dòng
        for idx, val in enumerate(row, start=1):
            ws.cell(row=row_num, column=idx, value=val)
        row_num += 1
    
    # 4. Hàng tổng cuối cùng
    # Viết "Tổng" vào cột 1
    ws.cell(row=row_num, column=1, value="Tổng").font = Font(bold=True)
    # Viết tổng số bữa ăn mỗi ngày
    for i, cnt in enumerate(totals_per_day, start=1):
        ws.cell(row=row_num, column=1 + i, value=cnt).font = Font(bold=True)
    # Để trống 2 cột cuối (Tổng + Thành tiền)
    ws.cell(row=row_num, column=2 + max_day + 1, value="").font = Font(bold=True)
    ws.cell(row=row_num, column=3 + max_day + 1, value="").font = Font(bold=True)
    
    # 5. Trả file
    resp = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    fname = f"ThongKe_{selected_year}_{selected_month}.xlsx"
    resp["Content-Disposition"] = f'attachment; filename="{fname}"'
    wb.save(resp)
    return resp
def export_yearly_statistics(request):
    year     = request.GET.get('year')
    class_id = request.GET.get('class_id')
    if not (year and class_id):
        return HttpResponse("Thiếu tham số", status=400)

    year_i    = int(year)
    classroom = get_object_or_404(ClassRoom, id=int(class_id))
    students  = Student.objects.filter(classroom=classroom).order_by('name')
    months    = list(range(1, 13))

    # --- Tạo workbook và sheet ---
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{year}-TiệnĂn"

    # --- Tiêu đề merge ---
    last_col = 2 + len(months)*3
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=last_col)
    title = f"THEO DÕI TIỀN ĂN CÁC THÁNG {year}   |   LỚP: {classroom.name}"
    c = ws.cell(row=1, column=1, value=title)
    c.alignment = Alignment(horizontal='center', vertical='center')
    c.font      = Font(size=14, bold=True)

    # --- Header tháng và sub-header ---
    ws.cell(row=3, column=1, value="STT").font = Font(bold=True)
    ws.cell(row=3, column=2, value="HỌ VÀ TÊN").font = Font(bold=True)
    for idx, m in enumerate(months):
        col_start = 3 + idx*3
        ws.merge_cells(start_row=3, start_column=col_start, end_row=3, end_column=col_start+2)
        h = ws.cell(row=3, column=col_start, value=f"THÁNG {m:02d}/{year}")
        h.alignment = Alignment(horizontal='center', vertical='center')
        h.font      = Font(bold=True)
        # sub-headers
        ws.cell(row=4, column=col_start,   value="Đã đóng").font = Font(bold=True)
        ws.cell(row=4, column=col_start+1, value="Ăn học").font = Font(bold=True)
        ws.cell(row=4, column=col_start+2, value="Còn lại").font = Font(bold=True)

    # --- Khởi tạo mảng tổng ---
    totals = [[Decimal('0'), Decimal('0'), Decimal('0')] for _ in months]

    # --- Điền dữ liệu từng học sinh ---
    row_num = 5
    for i, stu in enumerate(students, start=1):
        ws.cell(row=row_num, column=1, value=i)
        ws.cell(row=row_num, column=2, value=stu.name)
        for idx, m in enumerate(months):
            col = 3 + idx*3
            ym = f"{year}-{m:02d}"
            sp = StudentPayment.objects.filter(student=stu, month=ym).first()

            # Giá trị tiền
            paid      = sp.amount_paid if sp else Decimal('0')
            tuition   = sp.tuition_fee  if sp else Decimal('0')
            remaining = sp.remaining_balance if (sp and sp.remaining_balance is not None) else Decimal('0')

            # Tính spent = tuition + tiền ăn
            # Xác định phí ăn
            if sp:
                df = sp.daily_meal_fee
                if df == Decimal('30000'):
                    fee_lunch = Decimal('20000')
                elif df == Decimal('40000'):
                    fee_lunch = Decimal('30000')
                else:
                    fee_lunch = df - Decimal('10000')
            else:
                fee_lunch = Decimal('20000')
            fee_break = Decimal('10000')

            recs = MealRecord.objects.filter(
                student=stu,
                date__year=year_i,
                date__month=m,
                meal_type__in=["Bữa sáng","Bữa trưa"]
            )
            spent_meals = Decimal('0')
            for r in recs:
                if r.status == 'Đủ' or (r.status=='Thiếu' and r.non_eat==2):
                    spent_meals += fee_break if r.meal_type=="Bữa sáng" else fee_lunch

            spent = tuition + spent_meals

            # Cộng vào tổng lớp
            totals[idx][0] += paid
            totals[idx][1] += spent
            totals[idx][2] += remaining

            # Ghi vào ô
            ws.cell(row=row_num, column=col,   value=float(paid))
            ws.cell(row=row_num, column=col+1, value=float(spent))
            ws.cell(row=row_num, column=col+2, value=float(remaining))

        row_num += 1

    # --- Hàng Tổng ---
    ws.cell(row=row_num, column=1, value="Tổng").font = Font(bold=True)
    for idx, (tot_paid, tot_spent, tot_rem) in enumerate(totals):
        base = 3 + idx*3
        ws.cell(row=row_num, column=base,   value=float(tot_paid)).font = Font(bold=True)
        ws.cell(row=row_num, column=base+1, value=float(tot_spent)).font = Font(bold=True)
        ws.cell(row=row_num, column=base+2, value=float(tot_rem)).font = Font(bold=True)

    # --- Trả file ---
    resp = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp["Content-Disposition"] = f'attachment; filename="TheoDoiTienAn_{classroom.name}_{year}.xlsx"'
    wb.save(resp)
    return resp