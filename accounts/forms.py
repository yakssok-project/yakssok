from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from .constants import (
    HEALTH_INFO_CHOICES,
    HEALTH_NOTES_CHOICES,
    SURGERY_HISTORY_CHOICES,
)
from .models import CustomUser

REQUIRED_MSG = '필수 정보를 입력해주세요.'


class SignupStepForm(forms.Form):
    """회원가입 단계별 입력 폼."""

    def __init__(self, step, signup_data=None, *args, **kwargs):
        self.step = step
        self.signup_data = signup_data or {}
        super().__init__(*args, **kwargs)
        self._build_fields_for_step()

    def _build_fields_for_step(self):
        if self.step == 1:
            self.fields['name'] = forms.CharField(
                label='이름',
                max_length=100,
                error_messages={'required': REQUIRED_MSG},
                widget=forms.TextInput(attrs={
                    'placeholder': '이름을 입력해주세요',
                    'autocomplete': 'name',
                }),
            )
        elif self.step == 2:
            self.fields['phone_number'] = forms.CharField(
                label='전화번호',
                max_length=20,
                error_messages={'required': REQUIRED_MSG},
                widget=forms.TextInput(attrs={
                    'placeholder': '01012345678',
                    'inputmode': 'tel',
                    'autocomplete': 'tel',
                }),
            )
        elif self.step == 3:
            self.fields['password'] = forms.CharField(
                label='비밀번호',
                error_messages={'required': REQUIRED_MSG},
                widget=forms.PasswordInput(attrs={
                    'placeholder': '비밀번호를 입력해주세요',
                    'autocomplete': 'new-password',
                }),
            )
        elif self.step == 4:
            self.fields['password_confirm'] = forms.CharField(
                label='비밀번호 확인',
                error_messages={'required': REQUIRED_MSG},
                widget=forms.PasswordInput(attrs={
                    'placeholder': '비밀번호를 다시 입력해주세요',
                    'autocomplete': 'new-password',
                }),
            )
        elif self.step == 5:
            self.fields['birth_date'] = forms.DateField(
                label='생년월일',
                error_messages={'required': REQUIRED_MSG},
                widget=forms.DateInput(attrs={
                    'type': 'date',
                }),
            )
        elif self.step == 6:
            self.fields['health_info'] = forms.MultipleChoiceField(
                label='기존 질병',
                choices=HEALTH_INFO_CHOICES,
                required=False,
                widget=forms.CheckboxSelectMultiple,
            )
        elif self.step == 7:
            self.fields['surgery_history'] = forms.ChoiceField(
                label='수술 여부',
                choices=SURGERY_HISTORY_CHOICES,
                error_messages={'required': REQUIRED_MSG},
                widget=forms.RadioSelect,
            )
        elif self.step == 8:
            self.fields['health_notes'] = forms.ChoiceField(
                label='특이사항',
                choices=HEALTH_NOTES_CHOICES,
                error_messages={'required': REQUIRED_MSG},
                widget=forms.RadioSelect,
            )

    def clean(self):
        cleaned = super().clean()
        if self.step == 4:
            password = self.signup_data.get('password')
            password_confirm = cleaned.get('password_confirm')
            if password != password_confirm:
                raise forms.ValidationError('비밀번호가 일치하지 않습니다.')
        return cleaned

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if self.step == 2 and CustomUser.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError('이미 사용 중인 전화번호입니다.')
        return phone

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if self.step == 3 and password:
            validate_password(password)
        return password


class LoginForm(forms.Form):
    phone_number = forms.CharField(
        label='전화번호',
        max_length=20,
        widget=forms.TextInput(attrs={
            'placeholder': '01012345678',
            'inputmode': 'tel',
            'autocomplete': 'tel',
        }),
    )
    password = forms.CharField(
        label='비밀번호',
        widget=forms.PasswordInput(attrs={
            'placeholder': '비밀번호를 입력해주세요',
            'autocomplete': 'current-password',
        }),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        phone = cleaned.get('phone_number', '').strip()
        password = cleaned.get('password')
        if not phone or not password:
            raise forms.ValidationError('필수 정보를 입력해주세요.')
        self.user_cache = authenticate(
            self.request,
            username=phone,
            password=password,
        )
        if self.user_cache is None:
            raise forms.ValidationError(
                '전화번호와 비밀번호가 올바르지 않습니다.',
            )
        return cleaned

    def get_user(self):
        return self.user_cache
