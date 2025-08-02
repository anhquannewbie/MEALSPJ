from meals.admin import my_admin_site
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required, permission_required
from meals.views import logout_view,admin_logout_view,export_monthly_statistics_all,ajax_get_classes_by_term
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
    statistics_print_view,
    user_login,
)

urlpatterns = [
    # Admin logout fix (must be before admin/ to avoid conflicts)
    path('admin/logout/', admin_logout_view, name='admin_logout'),
    
    # Admin site
    path('admin/', my_admin_site.urls),

    # Authentication
    path('login/', user_login, name='login'),
    path(
        'statistics/print/',
        login_required(
            permission_required('meals.view_statistics', raise_exception=True)(
                statistics_print_view
            ),
            login_url='login'
        ),
        name='statistics_print'  # New route for print view
    ),
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
    path('ajax/get-classes-by-term/', ajax_get_classes_by_term, name='ajax_get_classes_by_term'),
    # Statistics and exports
    path(
      'statistics/',
      login_required(
        permission_required('meals.view_statistics', raise_exception=True)(
          statistics_view
        ),
        login_url='login'
      ),
      name='statistics'
    ),
    path('export/yearly/', export_yearly_statistics, name='export_yearly_statistics'),
    path(
      'export/monthly/all/',
      export_monthly_statistics_all,
      name='export_monthly_all'
    ),
    path('login/', user_login, name='login'),

    # Root URL: redirect to login
    path(
       '',
        login_required(home, login_url='/login/'),
        name='home'
    ),
]
