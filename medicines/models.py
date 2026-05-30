from django.conf import settings
from django.db import models


class UserMedicine(models.Model):
    """사용자 복용 약 정보."""

    DEFAULT_IMAGE = 'medicines/img/tylenol.jpg'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medicines',
        verbose_name='사용자',
    )
    medicine_name = models.CharField('약 이름', max_length=200)
    ingredient_name = models.CharField('성분명', max_length=200, blank=True)
    intake_time = models.CharField(
        '복용 시간',
        max_length=255,
        help_text='예: 08:00,12:00,18:00',
    )
    frequency = models.CharField('복용 횟수', max_length=100)
    is_active = models.BooleanField('복용 중', default=True)
    alarm_enabled = models.BooleanField('알림 사용', default=True)
    manufactured_date = models.DateField('제조일자', null=True, blank=True)
    remaining_quantity = models.PositiveIntegerField('남은 수량(정)', default=0)
    total_quantity = models.PositiveIntegerField('총 수량(정)', default=0)
    manufacturer = models.CharField('제조사', max_length=200, blank=True)
    appearance = models.CharField('성상', max_length=200, blank=True)
    mark_front = models.CharField('식별표시(앞)', max_length=100, blank=True)
    mark_back = models.CharField('식별표시(뒤)', max_length=100, blank=True)
    color = models.CharField('색깔', max_length=100, blank=True)
    image = models.CharField(
        '약 이미지',
        max_length=255,
        default=DEFAULT_IMAGE,
        help_text='static 기준 경로',
    )
    dose_per_day = models.PositiveIntegerField('하루 복용 횟수', default=1)
    duration_days = models.PositiveIntegerField('복용 일수', default=1)
    meal_timing = models.CharField(
        '식전/식후',
        max_length=20,
        choices=[
            ('before', '식사 전'),
            ('after', '식사 후'),
        ],
        default='after',
    )
    created_at = models.DateTimeField('등록일시', auto_now_add=True)

    class Meta:
        verbose_name = '복용 약'
        verbose_name_plural = '복용 약'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.medicine_name} ({self.user})'

    @property
    def quantity_display(self):
        """남은 복용량 표시 (예: 25정 / 40정)."""
        if self.total_quantity:
            return f'{self.remaining_quantity}정 / {self.total_quantity}정'
        return f'{self.remaining_quantity}정'

    @property
    def remaining_ratio(self):
        """남은 비율 (정렬용, 0~1)."""
        if not self.total_quantity:
            return 0
        return self.remaining_quantity / self.total_quantity

    @property
    def image_static_path(self):
        return self.image or self.DEFAULT_IMAGE
    
    @property
    def remaining_percent(self):
        """남은 비율 퍼센트, 0~100."""
        if not self.total_quantity:
            return 0
        return int((self.remaining_quantity / self.total_quantity) * 100)
