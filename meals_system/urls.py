from django.contrib import admin
from django.urls import path, include
from meals_system.views import home  # Chúng ta sẽ tạo view trang chủ ở meals_system/views.py
from meals.views import export_yearly_statistics,student_payment_edit,ajax_load_students,ajax_load_previous_balance,ajax_load_payment_details,ajax_load_mealdata,statistics_view,ajax_load_months,export_monthly_statistics
urlpatterns = [
    path('admin/', admin.site.urls),
    path('meals/', include('meals.urls', namespace='meals')),
    path('', home, name='home'),
    path('student-payment/edit/', student_payment_edit, name='student_payment_edit'),
    path('student-payment/edit/<int:pk>/', student_payment_edit, name='student_payment_edit'),
    path('ajax/load-students/', ajax_load_students, name='ajax_load_students'),
    path('ajax/load-previous-balance/', ajax_load_previous_balance, name='ajax_load_previous_balance'),
    path('ajax/load-payment-details/', ajax_load_payment_details, name='ajax_load_payment_details'),
    path('ajax/load-mealdata/', ajax_load_mealdata, name='ajax_load_mealdata'),
    path('statistics/', statistics_view, name='statistics'),
    path('ajax/load-months/', ajax_load_months, name='ajax_load_months'),
    path('export/excel/', export_monthly_statistics, name='export_excel'),
    path('export/yearly/', export_yearly_statistics, name='export_yearly_statistics'),

]
