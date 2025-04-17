from django.urls import path
from . import views
from .views import student_payment_edit, ajax_load_previous_balance,ajax_load_students,ajax_load_payment_details,ajax_load_mealdata,ajax_load_months
app_name = 'meals'

urlpatterns = [
    path('', views.meal_record_list, name='meal_list'),
    path('record/<int:pk>/', views.meal_record_detail, name='meal_detail'),
    path('ajax/load-students/', views.load_students, name='ajax_load_students'),
    path('record/bulk_new/', views.bulk_meal_record_create, name='meal_bulk_create'),
    path('record/bulk_save/', views.bulk_meal_record_save, name='meal_bulk_save'),
    path('student-payment/edit/', student_payment_edit, name='student_payment_edit'),
    path('student-payment/edit/<int:pk>/', student_payment_edit, name='student_payment_edit'),
    path('ajax/load-students/', ajax_load_students, name='ajax_load_students'),
    path('ajax/load-previous-balance/', ajax_load_previous_balance, name='ajax_load_previous_balance'),
    path('ajax/load-payment-details/', ajax_load_payment_details, name='ajax_load_payment_details'),
    path('ajax/load-mealdata/', ajax_load_mealdata, name='ajax_load_mealdata'),
    path('ajax/load-months/', ajax_load_months, name='ajax_load_months'),
    path('export/excel/', views.export_monthly_statistics, name='export_excel'),
    path('export/yearly/', views.export_yearly_statistics, name='export_yearly_statistics'),
]
