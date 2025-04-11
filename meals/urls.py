from django.urls import path
from . import views

app_name = 'meals'

urlpatterns = [
    path('', views.meal_record_list, name='meal_list'),
    path('record/<int:pk>/', views.meal_record_detail, name='meal_detail'),
    path('record/new/', views.meal_record_create, name='meal_create'),
    path('ajax/load-students/', views.load_students, name='ajax_load_students'),
]
