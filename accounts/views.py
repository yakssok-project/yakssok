from datetime import date

from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .constants import SIGNUP_SESSION_KEY, SIGNUP_STEP_KEY, TOTAL_SIGNUP_STEPS
from .forms import LoginForm, SignupStepForm
from .models import CustomUser

REQUIRED_SIGNUP_KEYS = {
    2: ['name'],
    3: ['name', 'phone_number'],
    4: ['name', 'phone_number', 'password'],
    5: ['name', 'phone_number', 'password'],
    6: ['name', 'phone_number', 'password', 'birth_date'],
    7: ['name', 'phone_number', 'password', 'birth_date'],
    8: ['name', 'phone_number', 'password', 'birth_date', 'surgery_history'],
}


def _get_signup_data(request):
    return request.session.get(SIGNUP_SESSION_KEY, {})


def _save_signup_field(request, step, cleaned_data):
    data = _get_signup_data(request)
    if step == 1:
        data['name'] = cleaned_data['name'].strip()
    elif step == 2:
        data['phone_number'] = cleaned_data['phone_number'].strip()
    elif step == 3:
        data['password'] = cleaned_data['password']
    elif step == 5:
        data['birth_date'] = cleaned_data['birth_date'].isoformat()
    elif step == 6:
        data['health_info'] = ','.join(cleaned_data.get('health_info') or [])
    elif step == 7:
        data['surgery_history'] = cleaned_data['surgery_history']
    elif step == 8:
        data['health_notes'] = cleaned_data['health_notes']
    request.session[SIGNUP_SESSION_KEY] = data
    request.session.modified = True


def _signup_initial(signup_data, step):
    """이전 단계에서 저장한 값으로 폼 초기값 구성."""
    initial = {}
    if step == 1 and signup_data.get('name'):
        initial['name'] = signup_data['name']
    elif step == 2 and signup_data.get('phone_number'):
        initial['phone_number'] = signup_data['phone_number']
    elif step == 5 and signup_data.get('birth_date'):
        initial['birth_date'] = signup_data['birth_date']
    elif step == 6 and signup_data.get('health_info'):
        initial['health_info'] = signup_data['health_info'].split(',')
    elif step == 7 and signup_data.get('surgery_history'):
        initial['surgery_history'] = signup_data['surgery_history']
    elif step == 8 and signup_data.get('health_notes'):
        initial['health_notes'] = signup_data['health_notes']
    return initial


def _create_user_from_session(request):
    data = _get_signup_data(request)
    return CustomUser.objects.create_user(
        phone_number=data['phone_number'],
        password=data['password'],
        name=data['name'],
        birth_date=date.fromisoformat(data['birth_date']),
        health_info=data.get('health_info', ''),
        surgery_history=data.get('surgery_history', ''),
        health_notes=data.get('health_notes', ''),
    )


def _clear_signup_session(request):
    request.session.pop(SIGNUP_SESSION_KEY, None)
    request.session.pop(SIGNUP_STEP_KEY, None)


@require_http_methods(['GET', 'POST'])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        step = int(
            request.POST.get('step')
            or request.GET.get('step')
            or request.session.get(SIGNUP_STEP_KEY, 1)
        )
    else:
        step = int(request.GET.get('step') or request.session.get(SIGNUP_STEP_KEY, 1))
    if step < 1 or step > TOTAL_SIGNUP_STEPS:
        step = 1

    signup_data = _get_signup_data(request)
    required = REQUIRED_SIGNUP_KEYS.get(step, [])
    if any(key not in signup_data for key in required):
        step = 1
        request.session[SIGNUP_STEP_KEY] = 1

    form = SignupStepForm(
        step,
        signup_data=signup_data,
        data=request.POST or None,
        initial=_signup_initial(signup_data, step),
    )

    if request.method == 'POST':
        if form.is_valid():
            _save_signup_field(request, step, form.cleaned_data)
            if step < TOTAL_SIGNUP_STEPS:
                next_step = step + 1
                request.session[SIGNUP_STEP_KEY] = next_step
                return redirect(f'/accounts/signup/?step={next_step}')
            user = _create_user_from_session(request)
            _clear_signup_session(request)
            login(request, user)
            return redirect('home')

    step_titles = {
        1: '이름을 입력해주세요',
        2: '전화번호를 입력해주세요',
        3: '비밀번호를 입력해주세요',
        4: '비밀번호를 다시 입력해주세요',
        5: '생년월일을 입력해주세요',
        6: '기존 질병을 선택해주세요',
        7: '수술 여부를 선택해주세요',
        8: '특이사항을 선택해주세요',
    }

    context = {
        'form': form,
        'step': step,
        'total_steps': TOTAL_SIGNUP_STEPS,
        'step_title': step_titles[step],
        'can_go_back': step > 1,
        'prev_step': step - 1,
    }
    return render(request, 'accounts/signup.html', context)


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('home')

    return render(request, 'accounts/login.html', {'form': form})


@require_http_methods(['POST', 'GET'])
def logout_view(request):
    logout(request)
    return redirect('login')
