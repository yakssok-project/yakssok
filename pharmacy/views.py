import json
import urllib.error
import urllib.parse
import urllib.request
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

KAKAO_CATEGORY_URL = 'https://dapi.kakao.com/v2/local/search/category.json'


def _validate_coords(lat: float, lng: float) -> bool:
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return False
    # 대한민국 대략 범위 (과도한 요청 방지)
    return 33.0 <= lat <= 39.0 and 124.0 <= lng <= 132.5


@login_required
def pharmacy_map_view(request):
    return render(
        request,
        'pharmacy/map.html',
        {
            'nav_active': 'pharmacy',
            'kakao_javascript_key': getattr(settings, 'KAKAO_JAVASCRIPT_KEY', '') or '',
            'kakao_configured': bool(
                getattr(settings, 'KAKAO_REST_API_KEY', '')
                and getattr(settings, 'KAKAO_JAVASCRIPT_KEY', '')
            ),
        },
    )


@login_required
@require_GET
def nearby_pharmacies_api(request):
    """카카오 로컬 API 카테고리 검색(PM9 약국), 거리순."""
    rest_key = getattr(settings, 'KAKAO_REST_API_KEY', '') or ''
    if not rest_key:
        return JsonResponse(
            {
                'ok': False,
                'error': '서버에 카카오 REST API 키가 설정되어 있지 않습니다. (.env 또는 settings)',
            },
            status=503,
        )

    try:
        lat = float(request.GET.get('lat', ''))
        lng = float(request.GET.get('lng', ''))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': '위도·경도가 올바르지 않습니다.'}, status=400)

    if not _validate_coords(lat, lng):
        return JsonResponse({'ok': False, 'error': '허용되지 않은 좌표입니다.'}, status=400)

    try:
        radius = int(request.GET.get('radius', '5000'))
    except ValueError:
        radius = 5000
    radius = max(500, min(radius, 20000))

    try:
        size = int(request.GET.get('size', '15'))
    except ValueError:
        size = 15
    size = max(1, min(size, 15))

    params = urllib.parse.urlencode(
        {
            'category_group_code': 'PM9',
            'x': lng,
            'y': lat,
            'radius': radius,
            'size': size,
            'sort': 'distance',
        }
    )
    url = f'{KAKAO_CATEGORY_URL}?{params}'
    req = urllib.request.Request(
        url,
        headers={'Authorization': f'KakaoAK {rest_key}'},
        method='GET',
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')
        return JsonResponse(
            {
                'ok': False,
                'error': f'카카오 API 오류 (HTTP {e.code})',
                'detail': err_body[:500],
            },
            status=502,
        )
    except urllib.error.URLError as e:
        return JsonResponse(
            {'ok': False, 'error': '카카오 API에 연결할 수 없습니다.', 'detail': str(e.reason)},
            status=502,
        )

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': '카카오 API 응답을 해석할 수 없습니다.'}, status=502)

    documents = data.get('documents') or []
    items = []
    for doc in documents:
        distance_m = doc.get('distance')
        try:
            distance_m = int(distance_m) if distance_m is not None else None
        except (TypeError, ValueError):
            distance_m = None

        phone = (doc.get('phone') or '').strip()
        name = (doc.get('place_name') or '').strip()
        road = (doc.get('road_address_name') or '').strip()
        jibun = (doc.get('address_name') or '').strip()
        address = road or jibun

        try:
            plat = float(doc.get('y'))
            plng = float(doc.get('x'))
        except (TypeError, ValueError):
            continue

        # 카테고리 검색 응답에는 영업시간 필드가 없음 — UI용 기본값
        items.append(
            {
                'id': doc.get('id') or f'{plat},{plng}',
                'name': name,
                'phone': phone,
                'address': address,
                'lat': plat,
                'lng': plng,
                'distance_m': distance_m,
                'category_name': (doc.get('category_name') or '').strip(),
                'place_url': (doc.get('place_url') or '').strip(),
                'business_status': '영업 정보 없음',
                'closing_time': '-',
            }
        )

    items.sort(key=lambda x: (x['distance_m'] is None, x['distance_m'] or 999999))

    return JsonResponse({'ok': True, 'items': items, 'meta': {'count': len(items)}})
