from django.contrib import admin
from .models import Student, MealRecord

class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_name')
    search_fields = ('name',)

class MealRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'meal_type', 'status')
    list_filter = ('date', 'meal_type')
    search_fields = ('student__name',)

admin.site.register(Student, StudentAdmin)
admin.site.register(MealRecord, MealRecordAdmin)
