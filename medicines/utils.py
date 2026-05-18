import re
from datetime import datetime, timedelta

from django.utils import timezone

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
