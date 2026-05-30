import re
from datetime import datetime, timedelta

from django.utils import timezone

import os
import json
from PIL import Image
from google import genai
from google.genai import types

TIME_PATTERN = re.compile(r'(\d{1,2}):(\d{2})')


def parse_intake_times(intake_time_str):
    """복용 시간 문자열에서 time 목록 추출."""
    times = []
    for match in TIME_PATTERN.finditer(intake_time_str or ''):
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour < 24 and 0 <= minute < 60:
            times.append((hour, minute))
    return sorted(times)


def minutes_until_next_intake(intake_time_str, now=None):
    """현재 시각 기준 다음 복용까지 남은 분 (작을수록 가까움)."""
    now = now or timezone.localtime()
    times = parse_intake_times(intake_time_str)
    if not times:
        return float('inf')

    best_minutes = None
    for hour, minute in times:
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        delta_minutes = (candidate - now).total_seconds() / 60
        if best_minutes is None or delta_minutes < best_minutes:
            best_minutes = delta_minutes
    return best_minutes


def format_next_intake(intake_time_str, now=None):
    """카드에 표시할 다음 복용 시각 문자열."""
    now = now or timezone.localtime()
    times = parse_intake_times(intake_time_str)
    if not times:
        return ''

    best_dt = None
    for hour, minute in times:
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        if best_dt is None or candidate < best_dt:
            best_dt = candidate

    if best_dt.date() == now.date():
        return best_dt.strftime('%H:%M')
    return best_dt.strftime('내일 %H:%M')


def format_intake_times_display(intake_time_str):
    """복용 시간 목록 표시용."""
    times = parse_intake_times(intake_time_str)
    return ', '.join(f'{h:02d}:{m:02d}' for h, m in times)


def sort_medicines_by_next_intake(medicines, now=None):
    """다음 복용이 가까운 순으로 정렬된 카드 데이터 목록."""
    now = now or timezone.localtime()
    items = []
    for medicine in medicines:
        items.append({
            'medicine': medicine,
            'next_minutes': minutes_until_next_intake(medicine.intake_time, now),
            'next_intake_label': format_next_intake(medicine.intake_time, now),
            'intake_times_display': format_intake_times_display(medicine.intake_time),
        })
    items.sort(key=lambda item: item['next_minutes'])
    return items


def extract_medicines_from_prescription(image_file):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY가 .env에 없습니다.")

    client = genai.Client(api_key=api_key)

    image = Image.open(image_file)

    prompt = """
너는 처방전 이미지에서 약 이름과 약물 사진 정보를 추출하는 도우미야.

이미지에서 확인 가능한 약 이름만 추출해.
복용법, 용량, 일수, 병원명, 환자명은 제외해.

약 이름 근처에 약물 사진 또는 알약 이미지가 보이면 has_image를 true로 표시해.
약물 사진의 위치를 알 수 있으면 bounding_box를 추정해.
bounding_box는 이미지 전체 기준으로 0~1000 사이 정규화 좌표 [x_min, y_min, x_max, y_max]로 답해.

반드시 아래 JSON 형식으로만 답해.

{
  "medicines": [
    {
      "name": "약 이름",
      "raw_text": "이미지에서 보이는 원문",
      "confidence": "high/medium/low",
      "has_image": true,
      "image_description": "보이는 약물 사진 설명",
      "bounding_box": [0, 0, 0, 0]
    }
  ]
}

약 이름을 확실히 모르겠으면 confidence를 low로 표시해.
약물 사진이 없거나 위치를 알 수 없으면 has_image는 false, bounding_box는 null로 표시해.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, image],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)


def explain_ddi_reason_with_gemini(reason):
    """
    금기사유 원문을 Gemini로 쉬운 설명으로 변환.
    실패하면 원문을 그대로 반환.
    """
    if not reason:
        return "복용 전 약사와 상담해주세요."

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return reason

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
다음은 두 약을 함께 복용할 때 주의해야 하는 금기 사유입니다.
이 내용을 일반 사용자가 이해하기 쉽고 짧게 한국어 2~3문장으로 설명해주세요.

금기사유: {reason}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        return response.text.strip() or reason

    except Exception as e:
        print("DDI Gemini explanation error:", e)
        return reason
    

# 더미데이터
DUMMY_MEDICINE_DETAILS = {
    "레보프라이드정": {
        "manufacturer": "SK케미칼",
        "ingredient_name": "Levosulpiride",
        "appearance": "백색의 원형 정제",
        "mark_front": "SK",
        "mark_back": "25",
        "color": "하양",
        "image": "medicines/img/레보프라이드.jpg",
    },

    "울메텍플러스정20/12.5mg": {
        "manufacturer": "한미약품",
        "ingredient_name": "Olmesartan medoxomil + Hydrochlorothiazide",
        "appearance": "적황색을 띄는 원형의 필름코팅정",
        "mark_front": "SANKYO",
        "mark_back": "C22",
        "color": "주황",
        "image": "medicines/img/올메텍플러스정.jpg",
    },

    "록소날정": {
        "manufacturer": "경동제약",
        "ingredient_name": "Loxoprofen Sodium",
        "appearance": "흰색∼미황색의 원형 정제",
        "mark_front": "LOT",
        "mark_back": "식별문자 없음",
        "color": "하양/미황색",
        "image": "medicines/img/록소날.jpg",
    },

    "바난정": {
        "manufacturer": "제일약품",
        "ingredient_name": "Cefpodoxime Proxetil",
        "appearance": "흰색-미황색의 필름코팅정",
        "mark_front": "BNT",
        "mark_back": "식별문자 없음",
        "color": "하양/미황색",
        "image": "medicines/img/바난정.jpg",
    },

    "비졸본정": {
        "manufacturer": "사노피-아벤티스코리아",
        "ingredient_name": "Bromhexine Hydrochloride",
        "appearance": "정제",
        "mark_front": "확인 필요",
        "mark_back": "확인 필요",
        "color": "확인 필요",
        "image": "medicines/img/비졸본정.jpg",
    },

    "싸이메트정": {
        "manufacturer": "확인 필요",
        "ingredient_name": "Cimetidine",
        "appearance": "담녹색의 필름코팅정",
        "mark_front": "확인 필요",
        "mark_back": "확인 필요",
        "color": "녹색",
        "image": "medicines/img/싸이메트정.jpg",
    },

    "엠티엑스주": {
        "manufacturer": "비씨월드제약",
        "ingredient_name": "Methotrexate",
        "appearance": "갈색 바이알에 충진된 담황색 주사액",
        "mark_front": "주사제",
        "mark_back": "주사제",
        "color": "담황색",
        "image": "medicines/img/엠티엑스주.jpg",
    },

    "올메텍플러스정": {
        "manufacturer": "대웅제약",
        "ingredient_name": "Olmesartan medoxomil + Hydrochlorothiazide",
        "appearance": "적황색을 띄는 원형의 필름코팅정",
        "mark_front": "SANKYO",
        "mark_back": "C22",
        "color": "주황",
        "image": "medicines/img/올메텍플러스정.jpg",
    },

    "한미아스피린장용정": {
        "manufacturer": "한미약품",
        "ingredient_name": "Aspirin",
        "appearance": "백색의 원형 장용성 필름코팅정제",
        "mark_front": "Aspirin",
        "mark_back": "100",
        "color": "하양",
        "image": "medicines/img/한미아스피린장용정.jpg",
    },
}

def get_dummy_medicine_detail(medicine_name):
    name = (medicine_name or "").strip()

    for dummy_name, detail in DUMMY_MEDICINE_DETAILS.items():
        if name == dummy_name:
            return detail

        if name.startswith(dummy_name):
            return detail

        if dummy_name.startswith(name):
            return detail

    return None

def apply_dummy_detail_to_medicine(medicine):
    dummy_detail = get_dummy_medicine_detail(medicine.medicine_name)

    if not dummy_detail:
        medicine.dummy_image_static_path = medicine.image_static_path
        return medicine

    medicine.manufacturer = dummy_detail.get("manufacturer")
    medicine.ingredient_name = dummy_detail.get("ingredient_name")
    medicine.appearance = dummy_detail.get("appearance")
    medicine.mark_front = dummy_detail.get("mark_front")
    medicine.mark_back = dummy_detail.get("mark_back")
    medicine.color = dummy_detail.get("color")

    # image_static_path는 property라 수정 불가
    # 대신 새 속성을 붙임
    medicine.dummy_image_static_path = dummy_detail.get("image")

    return medicine