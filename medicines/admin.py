from django.contrib import admin

from .models import UserMedicine


@admin.register(UserMedicine)
class UserMedicineAdmin(admin.ModelAdmin):
    list_display = (
        'medicine_name',
        'ingredient_name',
        'user',
        'manufactured_date',
        'remaining_quantity',
        'total_quantity',
        'is_active',
        'created_at',
    )
    list_filter = ('is_active', 'alarm_enabled')
    search_fields = (
        'medicine_name',
        'ingredient_name',
        'user__phone_number',
        'user__name',
    )
