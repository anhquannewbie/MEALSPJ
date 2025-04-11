from django.contrib import admin
from django.urls import path, include
from meals_system.views import home  # Chúng ta sẽ tạo view trang chủ ở meals_system/views.py

urlpatterns = [
    path('admin/', admin.site.urls),
    path('meals/', include('meals.urls', namespace='meals')),
    path('', home, name='home'),
]
