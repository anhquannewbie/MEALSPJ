from django.urls import path
from . import views
from .views import student_payment_edit, ajax_load_previous_balance,ajax_load_students
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
]
