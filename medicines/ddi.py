"""DDI(약물 상호작용) CSV 기반 위험 조합 탐지."""

import csv
from functools import lru_cache
from pathlib import Path

from django.conf import settings

CSV_PATH = Path(settings.BASE_DIR) / 'ddi_interactions_filtered.csv'

CSV_HEADERS = {
    'ingredient_name_1': '성분명1',
    'product_name_1': '제품명1',
    'ingredient_name_2': '성분명2',
    'product_name_2': '제품명2',
    'contraindication_reason': '금기사유',
}


def normalize_ingredient(name):
    return (name or '').strip().lower()


@lru_cache(maxsize=1)
def load_interaction_index():
    """성분 쌍 → 금기사유 인덱스 (최초 1회 로드)."""
    index = {}
    if not CSV_PATH.exists():
        return index

    with CSV_PATH.open(encoding='utf-8-sig', newline='') as csv_file:
        reader = csv.reader(csv_file)

        for row in reader:
            if len(row) < 5:
                continue

            ing1 = normalize_ingredient(row[0])
            ing2 = normalize_ingredient(row[2])

            if not ing1 or not ing2:
                continue

            pair_key = tuple(sorted([ing1, ing2]))

            if pair_key not in index:
                reason = row[4].strip()
                index[pair_key] = reason

    return index


def _group_medicines_by_ingredient(medicines):
    groups = {}
    for medicine in medicines:
        key = normalize_ingredient(medicine.ingredient_name)
        if not key:
            continue
        groups.setdefault(key, []).append(medicine)
    return groups


def _pick_pair(meds_a, meds_b, ing1, ing2):
    """서로 다른 약 2개 선택."""
    if ing1 == ing2:
        if len(meds_a) < 2:
            return None
        return meds_a[0], meds_a[1]
    return meds_a[0], meds_b[0]


def find_ddi_warnings(medicines):
    """
    복용 중 약 목록에서 CSV 기반 위험 조합 탐지.
    한 CSV 행의 성분 2개가 모두 사용자 약과 매칭되면 경고 반환.
    """
    active = [m for m in medicines if m.is_active and m.ingredient_name]
    if len(active) < 2:
        return []

    groups = _group_medicines_by_ingredient(active)
    user_ingredients = set(groups.keys())
    if len(user_ingredients) < 2 and not any(len(v) >= 2 for v in groups.values()):
        return []

    interaction_index = load_interaction_index()
    warnings = []
    seen_pairs = set()

    for pair_key, reason in interaction_index.items():
        ing1, ing2 = pair_key
        if ing1 not in user_ingredients or ing2 not in user_ingredients:
            continue

        medicine_pair = _pick_pair(groups[ing1], groups[ing2], ing1, ing2)
        if not medicine_pair:
            continue

        med_a, med_b = medicine_pair
        dedupe_key = tuple(sorted([med_a.pk, med_b.pk]))
        if dedupe_key in seen_pairs:
            continue
        seen_pairs.add(dedupe_key)

        warnings.append({
            'medicine_1': med_a,
            'medicine_2': med_b,
            'reason': reason or '복용 전 약사와 상담해주세요.',
            'ingredient_1': ing1,
            'ingredient_2': ing2,
        })

    # CSV에 없어도 동일 성분 약 2개 이상이면 경고
    for ingredient, meds in groups.items():
        if len(meds) < 2:
            continue
        dedupe_key = tuple(sorted([meds[0].pk, meds[1].pk]))
        if dedupe_key in seen_pairs:
            continue
        seen_pairs.add(dedupe_key)
        warnings.append({
            'medicine_1': meds[0],
            'medicine_2': meds[1],
            'reason': '동일 성분이 포함된 약을 함께 복용하면 부작용 위험이 높아질 수 있습니다.',
            'ingredient_1': ingredient,
            'ingredient_2': ingredient,
        })

    return warnings
