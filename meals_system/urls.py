from django.contrib import admin
from django.urls import path, include
from meals_system.views import home  # Chúng ta sẽ tạo view trang chủ ở meals_system/views.py
from meals.views import student_payment_edit,ajax_load_students,ajax_load_previous_balance,ajax_load_payment_details
urlpatterns = [
    path('admin/', admin.site.urls),
    path('meals/', include('meals.urls', namespace='meals')),
    path('', home, name='home'),
    path('student-payment/edit/', student_payment_edit, name='student_payment_edit'),
    path('student-payment/edit/<int:pk>/', student_payment_edit, name='student_payment_edit'),
    path('ajax/load-students/', ajax_load_students, name='ajax_load_students'),
    path('ajax/load-previous-balance/', ajax_load_previous_balance, name='ajax_load_previous_balance'),
    path('ajax/load-payment-details/', ajax_load_payment_details, name='ajax_load_payment_details'),
]
