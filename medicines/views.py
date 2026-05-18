import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static

from .ddi import find_ddi_warnings
from .models import UserMedicine
from .utils import sort_medicines_by_next_intake

SORT_MANUFACTURED = 'manufactured'
SORT_REMAINING = 'remaining'


def _active_medicines(user):
    return UserMedicine.objects.filter(user=user, is_active=True)


def _sort_medicines(queryset, sort_key):
    medicines = list(queryset)
    if sort_key == SORT_REMAINING:
        return sorted(
            medicines,
            key=lambda m: (m.remaining_ratio, m.remaining_quantity),
        )
    # 제조일순 (최신 제조일 먼저, 없으면 뒤로)
    return sorted(
        medicines,
        key=lambda m: (m.manufactured_date is None, m.manufactured_date),
        reverse=True,
    )


@login_required
def home_view(request):
    """홈 화면 — 현재 복용 중인 약 목록."""
    active_medicines = _active_medicines(request.user)
    medicine_items = sort_medicines_by_next_intake(active_medicines)
    medicine_count = len(medicine_items)

    context = {
        'user': request.user,
        'medicine_items': medicine_items,
        'medicine_count': medicine_count,
        'has_medicines': medicine_count > 0,
        'nav_active': 'home',
    }
    return render(request, 'medicines/home.html', context)


@login_required
def medicine_list_view(request):
    """내 약 목록."""
    sort_key = request.GET.get('sort', SORT_MANUFACTURED)
    if sort_key not in (SORT_MANUFACTURED, SORT_REMAINING):
        sort_key = SORT_MANUFACTURED

    active_medicines = _sort_medicines(_active_medicines(request.user), sort_key)
    all_user_medicines = list(_active_medicines(request.user))
    ddi_warnings = find_ddi_warnings(all_user_medicines)

    warnings_for_js = [
        {
            'medicine_1': {
                'id': w['medicine_1'].pk,
                'name': w['medicine_1'].medicine_name,
                'image': static(w['medicine_1'].image_static_path),
            },
            'medicine_2': {
                'id': w['medicine_2'].pk,
                'name': w['medicine_2'].medicine_name,
                'image': static(w['medicine_2'].image_static_path),
            },
            'reason': w['reason'],
        }
        for w in ddi_warnings
    ]

    print("DDI warnings json:", warnings_for_js)
    print("DDI warnings:", ddi_warnings)

    
    context = {
        'user': request.user,
        'medicines': active_medicines,
        'has_medicines': bool(active_medicines),
        'sort_key': sort_key,
        'sort_manufactured': SORT_MANUFACTURED,
        'sort_remaining': SORT_REMAINING,
        'ddi_warnings': ddi_warnings,
        'ddi_warnings_json': warnings_for_js,
        'has_ddi_warning': bool(ddi_warnings),
        'nav_active': 'medicines',
    }
    return render(request, 'medicines/medicine_list.html', context)


@login_required
def medicine_detail_view(request, pk):
    """약 상세."""
    medicine = get_object_or_404(UserMedicine, pk=pk, user=request.user)

    context = {
        'user': request.user,
        'medicine': medicine,
        'nav_active': 'medicines',
    }
    return render(request, 'medicines/medicine_detail.html', context)
