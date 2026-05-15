from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """약쏙 서비스 사용자 — 로그인 ID는 전화번호."""

    phone_number = models.CharField('전화번호', max_length=20, unique=True)
    name = models.CharField('이름', max_length=100)
    birth_date = models.DateField('생년월일')
    health_info = models.CharField('기존 질병', max_length=255, blank=True)
    surgery_history = models.CharField('수술 여부', max_length=100, blank=True)
    health_notes = models.CharField('특이사항', max_length=255, blank=True)
    created_at = models.DateTimeField('가입일시', auto_now_add=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자'

    def __str__(self):
        return f'{self.name} ({self.phone_number})'
