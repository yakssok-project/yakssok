from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('phone_number', 'name', 'birth_date', 'created_at', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('phone_number', 'name')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('개인 정보', {'fields': ('name', 'birth_date', 'health_info', 'surgery_history', 'health_notes')}),
        ('권한', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'name', 'birth_date', 'password1', 'password2'),
        }),
    )
