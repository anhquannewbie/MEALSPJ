from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'meals'

urlpatterns = [
    # Meal records
    path('', login_required(views.meal_record_list), name='meal_list'),
    path('record/<int:pk>/', login_required(views.meal_record_detail), name='meal_detail'),

    # Bulk create/save meal records
    path('record/bulk_new/', login_required(views.bulk_meal_record_create), name='meal_bulk_create'),
    path('record/bulk_save/', login_required(views.bulk_meal_record_save), name='meal_bulk_save'),

    # AJAX endpoints
    path('ajax/load-students/', login_required(views.load_students), name='ajax_load_students'),
    path('ajax/load-previous-balance/', login_required(views.ajax_load_previous_balance), name='ajax_load_previous_balance'),
    path('ajax/load-payment-details/', login_required(views.ajax_load_payment_details), name='ajax_load_payment_details'),
    path('ajax/load-mealdata/', login_required(views.ajax_load_mealdata), name='ajax_load_mealdata'),
    path('ajax/load-months/', login_required(views.ajax_load_months), name='ajax_load_months'),
    path('ajax/get-months/', views.ajax_get_months, name='ajax_get_months'),
    # Student payments
    path('student-payment/edit/', login_required(views.student_payment_edit), name='student_payment_edit'),
    path('student-payment/edit/<int:pk>/', login_required(views.student_payment_edit), name='student_payment_edit'),
    path('ajax/get-classes-by-term/', views.ajax_get_classes_by_term, name='ajax_get_classes_by_term'),
    # Statistics and exports
    path('statistics/', login_required(views.statistics_view), name='statistics'),
    path('export/yearly/', login_required(views.export_yearly_statistics), name='export_yearly_statistics'),
    path(
      'export/monthly/all/',
      views.export_monthly_statistics_all,
      name='export_monthly_all'
    ),
    # Payments alias (optional)
    path('payments/', login_required(views.student_payment_edit), name='payments'),
    path('ajax/load-meal-stats/',
         login_required(views.ajax_load_meal_stats),
         name='ajax_load_meal_stats'),
]
