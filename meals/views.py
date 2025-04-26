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
from .models import StudentPayment,MealPrice
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
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login as auth_login
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from .utils import get_current_price
@csrf_exempt


def logout_view(request):
    logout(request)
    return redirect('login')
def user_login(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)
            # nếu là staff (admin site) thì redirect luôn vào /admin/
            if user.is_staff:
                return redirect(reverse('admin:index'))
            # ngược lại về home
            return redirect('home')
        else:
            error = "Sai tên đăng nhập hoặc mật khẩu"
    return render(request, 'login.html', {'error': error})
@login_required(login_url='login')
@permission_required('meals.change_studentpayment', raise_exception=True)
def student_payment_edit(request, pk=None):
    classrooms = ClassRoom.objects.all()

    # Lấy đối tượng để edit (nếu có)
    if request.method == "GET" and request.GET.get('payment_id'):
        try:
            payment = StudentPayment.objects.get(id=request.GET.get('payment_id'))
        except StudentPayment.DoesNotExist:
            payment = None
    else:
        payment = get_object_or_404(StudentPayment, pk=pk) if pk else None

    if request.method == "POST":
        # Nếu tạo mới mà trùng student+month, bind luôn vào bản tồn tại
        student_id = request.POST.get('student')
        month_val  = request.POST.get('month')
        form_instance = payment
        if not payment and student_id and month_val:
            dup = StudentPayment.objects.filter(
                student_id=student_id, month=month_val
            ).first()
            if dup:
                form_instance = dup

        form = StudentPaymentForm(request.POST, instance=form_instance)
        if form.is_valid():
            # form.save() sẽ create nếu instance=None, hoặc update nếu instance!=None
            payment_obj = form.save()
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
        'form':             form,
        'classrooms':       classrooms,
        'is_edit':          var_is_edit,
        'breakfast_count':  breakfast_count,
        'lunch_count':      lunch_count,
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
            # có rồi thì lấy y nguyên
            price = payment.meal_price
            data['meal_price']           = str(price.pk)
            data['tuition_fee']          = str(payment.tuition_fee)
            data['daily_price']          = str(price.daily_price)
            data['breakfast_price']      = str(price.breakfast_price)
            data['lunch_price']          = str(price.lunch_price)
            data['amount_paid']          = str(payment.amount_paid)
            data['current_month_payment']= str(payment.remaining_balance)
        else:
            # Chưa có record tháng này -> load cấu hình & học phí từ bản ghi gần nhất
            prev_cfg = (
                StudentPayment.objects
                .filter(student_id=student_id, month__lt=month)
                .order_by('-month')
                .first()
            )
            if prev_cfg:
                price = prev_cfg.meal_price
                data['meal_price']      = str(price.pk)
                data['tuition_fee']     = str(prev_cfg.tuition_fee)
                data['daily_price']     = str(price.daily_price)
                data['breakfast_price'] = str(price.breakfast_price)
                data['lunch_price']     = str(price.lunch_price)
            else:
                # Không có lần nào trước đó
                data['meal_price']      = ''
                data['tuition_fee']     = ''
                data['daily_price']     = ''
                data['breakfast_price'] = ''
                data['lunch_price']     = ''
            # Các ô tiền đóng vẫn để trống
            data['amount_paid']         = ''
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
        data['daily_price'] = ''
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
        reason_data_str  = request.POST.get('reason_data', '{}')
        reason_data      = json.loads(reason_data_str)
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
                non_eat=non_eat,
                absence_reason=reason_data.get(sid, '').strip()
            )
            current_month = today.strftime("%Y-%m")
            sp = StudentPayment.objects.get(student=student, month=current_month)
            sp.save()
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
    class_name = request.GET.get('class_name')
    meal_type  = request.GET.get('meal_type')
    today = date.today()
    students   = Student.objects.filter(classroom__name=class_name).order_by('name')

    data = []
    for student in students:
        record = MealRecord.objects.filter(
            student=student, date=today, meal_type=meal_type
        ).first()

        if record:
            item = {
                'id':      student.id,
                'name':    student.name,
                'checked': (record.status == 'Đủ'),
                'non_eat': record.non_eat,
                'reason':  record.absence_reason or ''
            }
        else:
            # mặc định: tick Ăn đủ nhưng cho phép chỉnh non_eat=1 và reason=''
            item = {
                'id':      student.id,
                'name':    student.name,
                'checked': True,
                'non_eat': 1,
                'reason':  ''
            }
        data.append(item)

    return JsonResponse(data, safe=False)
@login_required(login_url='login')
@permission_required('meals.view_statistics', raise_exception=True)
def statistics_view(request):
    # Danh sách lớp và năm
    classrooms  = ClassRoom.objects.all().order_by('name')
    meal_dates   = MealRecord.objects.values_list('date', flat=True)
    years_set    = set(d.year for d in meal_dates)
    years_list   = sorted(years_set)

    # Đọc chung params
    mode               = request.GET.get('mode', 'month')
    selected_year      = request.GET.get('year')
    selected_month     = request.GET.get('month')
    selected_meal_type = request.GET.get('meal_type')
    selected_class_id  = request.GET.get('class_id')

    # Context cơ bản
    context = {
        'classrooms':         classrooms,
        'years_list':         years_list,
        'mode':               mode,
        'selected_year':      selected_year,
        'selected_month':     selected_month,
        'selected_meal_type': selected_meal_type,
        'selected_class_id':  selected_class_id,
        'all_months':         list(range(1, 13)),
    }

    # Build months_list cho chế độ tháng
    if selected_year:
        year_meals = MealRecord.objects.filter(date__year=int(selected_year))
        context['months_list'] = sorted({m.date.month for m in year_meals})
    else:
        context['months_list'] = []

    # --- Thống kê theo tháng (giữ nguyên) ---
    if mode == 'month' and selected_year and selected_month and selected_class_id:
        class_id_int = int(selected_class_id)
        students     = Student.objects.filter(classroom_id=class_id_int).order_by('name')
        year_i       = int(selected_year)
        month_i      = int(selected_month)
        max_day      = calendar.monthrange(year_i, month_i)[1]

        # Tính thống kê cho cả hai loại bữa sáng và bữa trưa
        stats = {}
        for mt in ['Bữa sáng', 'Bữa trưa']:
            recs = MealRecord.objects.filter(
                student__classroom_id=class_id_int,
                meal_type=mt,
                date__year=year_i,
                date__month=month_i
            )
            record_map = {(r.student_id, r.date.day): (r.status, r.non_eat) for r in recs}

            rows_mt = []
            totals_mt = [0] * max_day

            for stu in students:
                ym = f"{selected_year}-{selected_month.zfill(2)}"
                sp = StudentPayment.objects.filter(student=stu, month=ym).first()
                price     = sp.meal_price if sp else get_current_price()
                fee_break = price.breakfast_price
                fee_lunch = price.lunch_price

                # Với Bữa trưa: tính thêm Đã thu và Ăn Học
                if mt == 'Bữa trưa':
                    # số ngày ăn sáng và ăn trưa
                    br_count = MealRecord.objects.filter(
                        student=stu,
                        date__year=year_i, date__month=month_i,
                        meal_type='Bữa sáng'
                    ).filter(Q(status='Đủ') | Q(status='Thiếu', non_eat=2)).count()
                    lu_count = MealRecord.objects.filter(
                        student=stu,
                        date__year=year_i, date__month=month_i,
                        meal_type='Bữa trưa'
                    ).filter(Q(status='Đủ') | Q(status='Thiếu', non_eat=2)).count()
                    tuition_fee     = sp.tuition_fee if sp else 0
                    learning_cost   = int(tuition_fee) + br_count * fee_break + lu_count * fee_lunch
                    collected       = sp.amount_paid  if sp else 0

                days = []
                total_meals = 0
                total_cost  = 0

                for d in range(1, max_day + 1):
                    s_ne = record_map.get((stu.id, d))
                    if s_ne:
                        s, ne = s_ne
                        if s == 'Đủ':
                            mark = 'X'
                            total_meals += 1
                            cost_unit = fee_break if mt=='Bữa sáng' else fee_lunch
                            total_cost += cost_unit
                            totals_mt[d-1] += 1
                        elif s == 'Thiếu' and ne == 2:
                            mark = 'KP'              # <-- đổi thành KP
                            total_meals += 1         # vẫn tính là đã ăn
                            cost_unit = fee_break if mt=='Bữa sáng' else fee_lunch
                            total_cost += cost_unit
                            totals_mt[d-1] += 1
                        elif s == 'Thiếu' and ne == 1:
                            mark = 'P'
                        else:
                            mark = '0'
                    else:
                        mark = '0'
                    days.append(mark)

                # Tạo 1 bản ghi duy nhất, gộp tất cả các trường
                row_data = {
                    'student':     stu,
                    'days':        days,
                    'total_meals': total_meals,
                    'total_cost':  f"{int(total_cost):,}",
                }
                if mt == 'Bữa trưa':
                    row_data['tuition_fee']     = f"{int(tuition_fee):,}"
                    row_data['collected']       = f"{int(collected):,}"
                    row_data['learning_cost']  = f"{int(learning_cost):,}"
                rows_mt.append(row_data)
                    

            stats[mt] = {'rows': rows_mt, 'totals': totals_mt}

        context.update({
            'stats':        stats,
            'max_day_list': list(range(1, max_day + 1)),
        })

    # --- Thống kê theo năm (mới) ---
    if mode == 'year':
        s_year   = request.GET.get('start_year')
        s_month  = request.GET.get('start_month')
        e_year   = request.GET.get('end_year')
        e_month  = request.GET.get('end_month')

        today = date.today()
        def_e_year  = today.year
        def_e_month = today.month
        sm = def_e_month - 9
        sy = def_e_year
        if sm <= 0:
            sm += 12; sy -= 1

        if not (s_year and s_month and e_year and e_month):
            start_year, start_month = sy, sm
            end_year,   end_month   = def_e_year, def_e_month
        else:
            start_year, start_month = int(s_year), int(s_month)
            end_year,   end_month   = int(e_year), int(e_month)

        months = []
        y, m = start_year, start_month
        while (y < end_year) or (y == end_year and m <= end_month):
            months.append((y, m))
            if m == 12: m = 1; y += 1
            else:       m += 1

        rows_year = []
        totals    = [[0,0,0] for _ in months]
        if selected_class_id:
            cid      = int(selected_class_id)
            students = Student.objects.filter(classroom_id=cid).order_by('name')

            for stu in students:
                data_row = []
                for idx, (yy, mm) in enumerate(months):
                    ym = f"{yy}-{mm:02d}"
                    sp = StudentPayment.objects.filter(student=stu, month=ym).first()
                    paid      = sp.amount_paid if sp else Decimal('0')
                    tuition   = sp.tuition_fee if sp else Decimal('0')
                    remaining = sp.remaining_balance if (sp and sp.remaining_balance is not None) else Decimal('0')

                    price   = sp.meal_price if sp else get_current_price()
                    fee_b   = Decimal(price.breakfast_price)
                    fee_l   = Decimal(price.lunch_price)
                    recs    = MealRecord.objects.filter(
                        student=stu, date__year=yy, date__month=mm,
                        meal_type__in=["Bữa sáng","Bữa trưa"]
                    )
                    spent_meals = sum(
                        fee_b if r.meal_type=="Bữa sáng" else fee_l
                        for r in recs
                        if (r.status=='Đủ' or (r.status=='Thiếu' and r.non_eat==2))
                    )
                    spent = tuition + spent_meals

                    totals[idx][0] += int(paid)
                    totals[idx][1] += int(spent)
                    totals[idx][2] += int(remaining)

                    data_row.append({
                        'paid':      f"{int(paid):,}",
                        'spent':     f"{int(spent):,}",
                        'remaining': f"{int(remaining):,}",
                    })
                rows_year.append({'student': stu, 'data': data_row})

        totals_fmt = [[f"{x:,}" for x in triple] for triple in totals]

        context.update({
            'selected_start_year':  start_year,
            'selected_start_month': start_month,
            'selected_end_year':    end_year,
            'selected_end_month':   end_month,
            'months':               [{'year': y, 'month': m} for y,m in months],
            'rows_year':            rows_year,
            'totals_year_data':     totals_fmt,
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
    selected_class_id  = request.GET.get('class_id')
    
    if not (selected_year and selected_month and selected_class_id):
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
        price     = sp.meal_price if sp else get_current_price()
        fee_break = price.breakfast_price
        fee_lunch = price.lunch_price
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
    # 1. Nhận tham số
    s_year   = request.GET.get('start_year')
    s_month  = request.GET.get('start_month')
    e_year   = request.GET.get('end_year')
    e_month  = request.GET.get('end_month')
    class_id = request.GET.get('class_id')
    if not (s_year and s_month and e_year and e_month and class_id):
        return HttpResponse("Thiếu tham số", status=400)

    # 2. Chuyển kiểu
    start_year, start_month = int(s_year), int(s_month)
    end_year,   end_month   = int(e_year),   int(e_month)

    # 3. Build danh sách tháng
    months = []
    y, m = start_year, start_month
    while (y < end_year) or (y == end_year and m <= end_month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    # 4. Lấy lớp & danh sách học sinh
    classroom = get_object_or_404(ClassRoom, id=int(class_id))
    students  = Student.objects.filter(classroom=classroom).order_by('name')

    # 5. Tạo workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    # Đặt tiêu đề sheet không chứa ký tự đặc biệt
    ws.title = f"{start_month:02d}{start_year}-{end_month:02d}{end_year}"

    # 6. Merge header & tiêu đề
    last_col = 2 + len(months)*3
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=last_col)
    title = (
        f"THEO DÕI TIỀN ĂN TỪ THÁNG {start_month:02d}/{start_year} "
        f"ĐẾN THÁNG {end_month:02d}/{end_year}   |   LỚP: {classroom.name}"
    )
    c = ws.cell(row=1, column=1, value=title)
    c.alignment = Alignment(horizontal='center', vertical='center')
    c.font      = Font(size=14, bold=True)

    # 7. Header các cột
    ws.cell(row=3, column=1, value="STT").font      = Font(bold=True)
    ws.cell(row=3, column=2, value="HỌ VÀ TÊN").font = Font(bold=True)
    for idx, (yy, mm) in enumerate(months):
        col = 3 + idx*3
        ws.merge_cells(start_row=3, start_column=col, end_row=3, end_column=col+2)
        h = ws.cell(row=3, column=col, value=f"THÁNG {mm:02d}/{yy}")
        h.alignment = Alignment(horizontal='center', vertical='center')
        h.font      = Font(bold=True)
        ws.cell(row=4, column=col,   value="Đã đóng").font = Font(bold=True)
        ws.cell(row=4, column=col+1, value="Ăn học").font = Font(bold=True)
        ws.cell(row=4, column=col+2, value="Còn lại").font = Font(bold=True)

    # 8. Khởi tạo mảng tổng
    totals = [[Decimal('0'), Decimal('0'), Decimal('0')] for _ in months]

    # 9. Điền dữ liệu học sinh
    row_num = 5
    for i, stu in enumerate(students, start=1):
        ws.cell(row=row_num, column=1, value=i)
        ws.cell(row=row_num, column=2, value=stu.name)
        for idx, (yy, mm) in enumerate(months):
            # Tìm StudentPayment theo tháng
            month_str = f"{yy:04d}-{mm:02d}"
            sp = StudentPayment.objects.filter(student=stu, month=month_str).first()
            if sp:
                paid = sp.amount_paid
                tuition = sp.tuition_fee
                rem    = sp.remaining_balance
                # Số ngày ăn sáng
                br_count = MealRecord.objects.filter(
                    student=stu,
                    date__year=yy,
                    date__month=mm,
                    meal_type="Bữa sáng"
                ).filter(
                    Q(status='Đủ') | Q(status='Thiếu', non_eat=2)
                ).count()
                # Số ngày ăn trưa
                lu_count = MealRecord.objects.filter(
                    student=stu,
                    date__year=yy,
                    date__month=mm,
                    meal_type="Bữa trưa"
                ).filter(
                    Q(status='Đủ') | Q(status='Thiếu', non_eat=2)
                ).count()
                fee_break = sp.meal_price.breakfast_price
                fee_lunch = sp.meal_price.lunch_price
                spent = tuition + Decimal(br_count) * Decimal(fee_break) + Decimal(lu_count) * Decimal(fee_lunch)
            else:
                paid = Decimal('0'); spent = Decimal('0'); rem = Decimal('0')

            # Cộng vào totals
            totals[idx][0] += paid
            totals[idx][1] += spent
            totals[idx][2] += rem

            # Ghi vào Excel với format số
            base = 3 + idx*3
            cells = [
                ws.cell(row=row_num, column=base,   value=float(paid)),
                ws.cell(row=row_num, column=base+1, value=float(spent)),
                ws.cell(row=row_num, column=base+2, value=float(rem)),
            ]
            for cell in cells:
                cell.font = Font(bold=False)
                cell.number_format = '#,##0'
        row_num += 1

    # 10. Hàng tổng
    ws.cell(row=row_num, column=1, value="Tổng").font = Font(bold=True)
    for idx, (p, s, r) in enumerate(totals):
        base = 3 + idx*3
        c1 = ws.cell(row=row_num, column=base,   value=float(p)); c1.font = Font(bold=True)
        c2 = ws.cell(row=row_num, column=base+1, value=float(s)); c2.font = Font(bold=True)
        c3 = ws.cell(row=row_num, column=base+2, value=float(r)); c3.font = Font(bold=True)
        for cell in (c1, c2, c3):
            cell.number_format = '#,##0'

    # 11. Trả file
    resp = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp["Content-Disposition"] = (
        f'attachment; filename="TheoDoiTienAn_{classroom.name}_'
        f'{start_month:02d}{start_year}-{end_month:02d}{end_year}.xlsx"'
    )
    wb.save(resp)
    return resp

def ajax_load_meal_stats(request):
    """
    Trả về 2 object: breakfast và lunch, mỗi object có:
      - days: mảng ['X','0',...]
      - total: tổng số bữa đã ăn
      - cost: tổng tiền (số nguyên, chưa format)
    """
    student_id = request.GET.get('student_id')
    month_str  = request.GET.get('month')  # "YYYY-MM"
    data = {'breakfast': {}, 'lunch': {}}

    if student_id and month_str:
        # parse year/month
        year, month = map(int, month_str.split('-'))
        max_day = calendar.monthrange(year, month)[1]

        # lấy fee để tính thành tiền
        sp = StudentPayment.objects.filter(student_id=student_id, month=month_str).first()
        price     = sp.meal_price if sp else get_current_price()
        fee_break = Decimal(price.breakfast_price)
        fee_lunch = Decimal(price.lunch_price)

        # load tất cả MealRecord của tháng
        recs = MealRecord.objects.filter(
            student_id=student_id,
            date__year=year,
            date__month=month,
            meal_type__in=["Bữa sáng","Bữa trưa"]
        )
        # map (meal_type,day) -> (status, non_eat)
        record_map = {
            (r.meal_type, r.date.day): (r.status, r.non_eat)
            for r in recs
        }

        # build breakfast
        br_days = []
        br_count = 0
        for d in range(1, max_day+1):
            s = record_map.get(("Bữa sáng", d))
            if s and (s[0]=="Đủ" or (s[0]=="Thiếu" and s[1]==2)):
                br_days.append("X")
                br_count += 1
            else:
                br_days.append("0")
        data['breakfast'] = {
            'days': br_days,
            'total': br_count,
            'cost': int(br_count * fee_break)
        }

        # build lunch
        lu_days = []
        lu_count = 0
        for d in range(1, max_day+1):
            s = record_map.get(("Bữa trưa", d))
            if s and (s[0]=="Đủ" or (s[0]=="Thiếu" and s[1]==2)):
                lu_days.append("X")
                lu_count += 1
            else:
                lu_days.append("0")
        data['lunch'] = {
            'days': lu_days,
            'total': lu_count,
            'cost': int(lu_count * fee_lunch)
        }

    return JsonResponse(data)

def export_monthly_statistics_all(request):
    year = request.GET.get('year')
    month = request.GET.get('month')
    class_id = request.GET.get('class_id')
    if not (year and month and class_id):
        return HttpResponse("Thiếu tham số", status=400)

    year_i = int(year)
    month_i = int(month)
    max_day = calendar.monthrange(year_i, month_i)[1]

    classroom = get_object_or_404(ClassRoom, id=int(class_id))
    students = Student.objects.filter(classroom=classroom).order_by('name')

    wb = openpyxl.Workbook()
    # loop qua hai loại bữa ăn
    for idx_mt, mt in enumerate(["Bữa sáng", "Bữa trưa"]):
        if idx_mt == 0:
            ws = wb.active
            ws.title = mt
        else:
            ws = wb.create_sheet(title=mt)

        # Tiêu đề
        last_col = 3 + max_day + (3 if mt == "Bữa trưa" else 0)
        ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=last_col)
        title = f"TK {mt.upper()} THÁNG {month}/{year} - LỚP {classroom.name}"
        c = ws.cell(row=1, column=1, value=title)
        c.alignment = Alignment(horizontal='center', vertical='center')
        c.font = Font(size=14, bold=True)

        # Header
        headers = ["Học sinh"] + [str(d) for d in range(1, max_day+1)] + ["Tổng", "Thành tiền"]
        if mt == "Bữa trưa":
            headers += ["Học phí", "Đã thu", "Ăn Học"]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=3, column=col_idx, value=h)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            ws.column_dimensions[get_column_letter(col_idx)].width = (12 if col_idx <= 2 else 5)

        # Dữ liệu từng học sinh
        row_num = 4
        for stu in students:
            # lấy giá
            sp = StudentPayment.objects.filter(student=stu, month=f"{year}-{int(month):02d}").first()
            fee_break = (sp.meal_price.breakfast_price if sp else get_current_price().breakfast_price)
            fee_lunch = (sp.meal_price.lunch_price     if sp else get_current_price().lunch_price)

            # build ngày
            recs = MealRecord.objects.filter(
                student=stu, meal_type=mt,
                date__year=year_i, date__month=month_i
            )
            rec_map = {r.date.day: (r.status, r.non_eat) for r in recs}

            days = []
            total_meals = 0
            total_cost = 0
            for d in range(1, max_day+1):
                val = rec_map.get(d)
                if val:
                    status, ne = val
                    if status == "Đủ":
                        mark = "X"
                        total_meals += 1
                        cost_unit = fee_break if mt == "Bữa sáng" else fee_lunch
                        total_cost += cost_unit
                    elif status == "Thiếu" and ne == 2:
                        mark = "KP"            # <-- đổi thành KP
                        total_meals += 1       # vẫn tính là đã ăn
                        cost_unit = fee_break if mt == "Bữa sáng" else fee_lunch
                        total_cost += cost_unit
                    elif status == "Thiếu" and ne == 1:
                        mark = "P"
                    else:
                        mark = "0"
                else:
                    mark = "0"
                days.append(mark)

            # thêm cột chung
            row = [stu.name] + days + [total_meals, total_cost]

            # với bữa trưa thêm 3 cột cuối
            if mt == "Bữa trưa":
                tuition_fee   = sp.tuition_fee if sp else 0
                collected     = sp.amount_paid  if sp else 0
                # học phí + ăn học = tuition_fee + tổng chi phí bữa sáng + trưa
                # tận dụng fee_break, fee_lunch và total_meals
                br_count = MealRecord.objects.filter(
                    student=stu, date__year=year_i, date__month=month_i, meal_type="Bữa sáng"
                ).filter(Q(status="Đủ")|Q(status="Thiếu", non_eat=2)).count()
                learning_cost = int(tuition_fee) + br_count * fee_break + total_meals * fee_lunch
                row += [tuition_fee, collected, learning_cost]

            # ghi vào sheet và format số
            for col_idx, val in enumerate(row, start=1):
                c = ws.cell(row=row_num, column=col_idx, value=val)
                if isinstance(val, (int, float, Decimal)):
                    c.number_format = '#,##0'
            row_num += 1

    # xuất file
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="ThongKe_{year}_{month}_ALL.xlsx"'
    wb.save(response)
    return response