from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home_view(request):
    """로그인 후 이동하는 홈 화면 (약 목록은 이후 단계에서 구현)."""
    return render(request, 'home.html', {'user': request.user})
