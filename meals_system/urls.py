from meals.admin import my_admin_site
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from meals.views import logout_view
# Views
from meals_system.views import home
from meals.views import (
    export_yearly_statistics,
    student_payment_edit,
    ajax_load_students,
    ajax_load_previous_balance,
    ajax_load_payment_details,
    ajax_load_mealdata,
    statistics_view,
    ajax_load_months,
    export_monthly_statistics,
    user_login,
)

urlpatterns = [
    # Admin site
    path('admin/', my_admin_site.urls),

    # Authentication
    path('login/', user_login, name='login'),

    # Meals app
    path('meals/', include('meals.urls', namespace='meals')),
    # AJAX endpoints and utilities
    path('student-payment/edit/', student_payment_edit, name='student_payment_edit'),
    path('student-payment/edit/<int:pk>/', student_payment_edit, name='student_payment_edit'),
    path('ajax/load-students/', ajax_load_students, name='ajax_load_students'),
    path('ajax/load-previous-balance/', ajax_load_previous_balance, name='ajax_load_previous_balance'),
    path('ajax/load-payment-details/', ajax_load_payment_details, name='ajax_load_payment_details'),
    path('ajax/load-mealdata/', ajax_load_mealdata, name='ajax_load_mealdata'),
    path('ajax/load-months/', ajax_load_months, name='ajax_load_months'),
    path('logout/', logout_view, name='logout'),
    # Statistics and exports
    path('statistics/', statistics_view, name='statistics'),
    path('export/excel/', export_monthly_statistics, name='export_excel'),
    path('export/yearly/', export_yearly_statistics, name='export_yearly_statistics'),

    # Root URL: redirect to login
    path(
       '',
        login_required(home, login_url='/login/'),
        name='home'
    ),
]
