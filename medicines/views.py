import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.templatetags.static import static

from .ddi import find_ddi_warnings
from .models import UserMedicine
from .utils import sort_medicines_by_next_intake
from .utils import explain_ddi_reason_with_gemini
from .utils import extract_medicines_from_prescription
from .utils import get_dummy_medicine_detail
from .utils import apply_dummy_detail_to_medicine

import csv
from pathlib import Path
from django.conf import settings

from .models import UserMedicine

from django.http import JsonResponse
from django.utils import timezone
from django.templatetags.static import static
from .utils import parse_intake_times
from django.urls import reverse

from .models import UserMedicine, IntakeLog
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

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

def short_medicine_name(name):
    return name.split("(")[0].strip()

@login_required
def home_view(request):
    def format_time(time_text):
        if not time_text:
            return ""

        try:
            hour, minute = time_text.split(":")
            hour = int(hour)

            period = "오전" if hour < 12 else "오후"
            display_hour = hour if hour <= 12 else hour - 12

            if display_hour == 0:
                display_hour = 12

            return f"{period} {display_hour}:{minute}"
        except Exception:
            return time_text

    active_medicines = _active_medicines(request.user)
    medicine_items = sort_medicines_by_next_intake(active_medicines)

    today = timezone.localdate()

    intake_logs = IntakeLog.objects.filter(
        user=request.user,
        intake_date=today,
    )

    log_map = {
        (log.medicine_id, log.intake_time): log.status
        for log in intake_logs
    }

    for item in medicine_items:
        medicine = item["medicine"]

        first_time = ""
        if medicine.intake_time:
            first_time = medicine.intake_time.split(",")[0].strip()

        meal_timing = ""
        if medicine.meal_timing == "before":
            meal_timing = "식전"
        elif medicine.meal_timing == "after":
            meal_timing = "식후"

        item["current_intake_time"] = first_time
        item["display_time"] = format_time(first_time)
        item["display_meal_timing"] = meal_timing
        item["intake_status"] = log_map.get((medicine.pk, first_time))

    medicine_count = len(medicine_items)

    context = {
        "user": request.user,
        "medicine_items": medicine_items,
        "medicine_count": medicine_count,
        "has_medicines": medicine_count > 0,
        "nav_active": "home",
    }

    return render(request, "medicines/home.html", context)

@login_required
def medicine_list_view(request):
    """내 약 목록."""
    sort_key = request.GET.get('sort', SORT_MANUFACTURED)
    if sort_key not in (SORT_MANUFACTURED, SORT_REMAINING):
        sort_key = SORT_MANUFACTURED

    active_medicines = _sort_medicines(_active_medicines(request.user), sort_key)
    
    active_medicines = [
    apply_dummy_detail_to_medicine(medicine)
    for medicine in active_medicines
    ]

    all_user_medicines = [
    apply_dummy_detail_to_medicine(medicine)
    for medicine in _active_medicines(request.user)
    ]

    ddi_warnings = find_ddi_warnings(all_user_medicines)

    warnings_for_js = []
    ddi_warned_ids = set()

    for w in ddi_warnings:
        original_reason = w["reason"]
        easy_reason = explain_ddi_reason_with_gemini(original_reason)

        warnings_for_js.append({
            "medicine_1": {
                "id": w["medicine_1"].pk,
                "name": short_medicine_name(w["medicine_1"].medicine_name),
                "image": static(w["medicine_1"].dummy_image_static_path),
            },
            "medicine_2": {
                "id": w["medicine_2"].pk,
                "name": short_medicine_name(w["medicine_2"].medicine_name),
                "image": static(w["medicine_2"].dummy_image_static_path),
            },
            "reason": original_reason,
            "easy_reason": easy_reason,
        })
    for w in ddi_warnings:
        ddi_warned_ids.add(w["medicine_1"].pk)
        ddi_warned_ids.add(w["medicine_2"].pk)

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
        'ddi_warned_ids': ddi_warned_ids,
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
        'nav_active': 'reminder',
        'back_url': reverse('medication_reminder'),
    }
    return render(request, 'medicines/medicine_detail.html', context)

@login_required
def medication_reminder_view(request):
    """복약 관리 / 약 영양제 복용기록 화면."""

    medicines = UserMedicine.objects.filter(
        user=request.user,
        is_active=True,
        alarm_enabled=True,
    ).order_by("created_at")

    ddi_warnings = find_ddi_warnings(list(medicines))
    warning_medicine_ids = set()

    for warning in ddi_warnings:
        warning_medicine_ids.add(warning["medicine_1"].pk)
        warning_medicine_ids.add(warning["medicine_2"].pk)

    today = timezone.localdate()

    intake_logs = IntakeLog.objects.filter(
        user=request.user,
        intake_date=today,
    )

    log_map = {
        (log.medicine_id, log.intake_time): log.status
        for log in intake_logs
    }

    groups = {}

    def format_time(time_text):
        try:
            hour, minute = time_text.split(":")
            hour = int(hour)

            period = "오전" if hour < 12 else "오후"
            display_hour = hour if hour <= 12 else hour - 12

            if display_hour == 0:
                display_hour = 12

            return f"{period} {display_hour}:{minute}"
        except Exception:
            return time_text

    for medicine in medicines:
        times = [
            t.strip()
            for t in medicine.intake_time.split(",")
            if t.strip()
        ]

        for time in times:
            timing = "식후" if medicine.meal_timing == "after" else "식전"
            key = (time, timing)

            if key not in groups:
                groups[key] = {
                    "time": format_time(time),
                    "raw_time": time,
                    "timing": timing,
                    "medicines": [],
                }

            if medicine.total_quantity:
                taken_quantity = medicine.total_quantity - medicine.remaining_quantity
                progress = int((taken_quantity / medicine.total_quantity) * 100)
            else:
                progress = 0

            dummy_detail = get_dummy_medicine_detail(medicine.medicine_name)

            image_static_path = (
                dummy_detail["image"]
                if dummy_detail
                else medicine.image_static_path
            )

            groups[key]["medicines"].append({
                "pk": medicine.pk,
                "name": medicine.medicine_name,
                "image_static_path": image_static_path,
                "progress": progress,
                "is_warning": medicine.pk in warning_medicine_ids,
                "intake_status": log_map.get((medicine.pk, time)),
            })

    medication_groups = [
        groups[key]
        for key in sorted(groups.keys())
    ]

    return render(request, "medicines/medication_reminder.html", {
        "user": request.user,
        "medication_groups": medication_groups,
        "has_medication_groups": bool(medication_groups),
        "nav_active": "reminder",
    })

def prescription_upload(request):
    if request.method == "POST":
        image_file = request.FILES.get("prescription_image")

        result = extract_medicines_from_prescription(image_file)

        request.session["ocr_result"] = result

        return redirect("prescription_result")

    return render(request, "medicines/prescription_upload.html", {
        "nav_active": "scan",
    })


def prescription_result(request):
    result = request.session.get("ocr_result")

    if not result:
        return redirect("prescription_upload")

    return render(request, "medicines/prescription_result.html", {
        "medicines": result["medicines"],
        "nav_active": "scan",
    })

@login_required
def prescription_camera(request):
    return render(request, "medicines/prescription_camera.html")

@login_required
def prescription_preview(request):
    return render(request, "medicines/prescription_preview.html")

@login_required
def prescription_loading(request):
    if request.method == "POST":
        image = request.FILES.get("image")

        if not image:
            return redirect("prescription_preview")

        try:
            result = extract_medicines_from_prescription(image)
        except Exception as e:
            print("OCR ERROR:", e)
            result = {
                "medicines": [],
                "error": "OCR 분석에 실패했어요."
            }

        request.session["ocr_result"] = result

        return redirect("prescription_result")

    return redirect("home")

@login_required
def prescription_result(request):
    result = request.session.get("ocr_result", {})
    medicines = result.get("medicines", [])
    error = result.get("error")

    return render(request, "medicines/prescription_result.html", {
        "medicines": medicines,
        "error": error,
    })

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

@login_required
def medicine_search_add(request):
    query = request.GET.get("q", "").strip()
    medicines = []

    csv_path = Path(settings.BASE_DIR) / "ddi_interactions_filtered.csv"

    if query and csv_path.exists():
        seen = set()

        with csv_path.open(encoding="utf-8-sig", newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                candidates = [
                    {
                        "product_name": row.get("제품명1", "").strip(),
                        "ingredient_name": row.get("성분명1", "").strip(),
                    },
                    {
                        "product_name": row.get("제품명2", "").strip(),
                        "ingredient_name": row.get("성분명2", "").strip(),
                    },
                ]

                for item in candidates:
                    product_name = item["product_name"]

                    if not product_name:
                        continue

                    if query.lower() not in product_name.lower():
                        continue

                    if product_name in seen:
                        continue

                    seen.add(product_name)
                    medicines.append(item)

                    if len(medicines) >= 20:
                        break

                if len(medicines) >= 20:
                    break

    return render(request, "medicines/medicine_search_add.html", {
        "query": query,
        "medicines": medicines,
    })

@login_required
def medicine_search_select(request):
    if request.method == "POST":
        name = request.POST.get("name", "")
        ingredient = request.POST.get("ingredient", "")

        request.session["ocr_result"] = {
            "medicines": [
                {
                    "name": name,
                    "ingredient_name": ingredient,
                    "frequency": "?",
                    "duration": "?",
                    "confidence": "manual",
                }
            ]
        }

        return redirect("prescription_result")

    return redirect("medicine_search_add")


@login_required
def medicine_edit_temp(request, index):
    result = request.session.get("ocr_result", {})
    medicines = result.get("medicines", [])

    if index >= len(medicines):
        return redirect("prescription_result")

    med = medicines[index]

    if request.method == "POST":
        med["frequency"] = request.POST.get("frequency", "1")
        med["duration"] = request.POST.get("duration", "1")
        med["meal_timing"] = request.POST.get("meal_timing", "after")
        med["alarm_enabled"] = request.POST.get("alarm_enabled") == "on"
        med["alarm_times"] = request.POST.getlist("alarm_times")

        request.session["ocr_result"] = result
        request.session.modified = True

        return redirect("prescription_result")

    return render(request, "medicines/medicine_edit_temp.html", {
        "med": med,
        "index": index,
    })

@login_required
def prescription_save(request):
    if request.method != "POST":
        return redirect("prescription_result")

    result = request.session.get("ocr_result", {})
    medicines = result.get("medicines", [])

    if not medicines:
        return redirect("prescription_result")

    existing_medicines = UserMedicine.objects.filter(
        user=request.user,
        is_active=True
    )

    # 지금은 기존 약 존재 여부만 확인.
    # 나중에 여기서 find_ddi_warnings() 연결해서 경고 화면으로 보낼 예정.
    has_existing_medicines = existing_medicines.exists()

    for med in medicines:
        frequency = med.get("frequency") or "1"
        duration = med.get("duration") or "1"

        if frequency == "?":
            frequency = "1"

        if duration == "?":
            duration = "1"

        frequency_int = int(frequency)
        duration_int = int(duration)

        alarm_times = med.get("alarm_times") or ["09:00"]
        alarm_enabled = med.get("alarm_enabled", True)

        UserMedicine.objects.create(
            user=request.user,
            medicine_name=med.get("name", ""),
            ingredient_name=med.get("ingredient_name", ""),
            intake_time=",".join(alarm_times),
            frequency=f"하루 {frequency_int}번",
            dose_per_day=frequency_int,
            duration_days=duration_int,
            meal_timing=med.get("meal_timing", "after"),
            remaining_quantity=frequency_int * duration_int,
            total_quantity=frequency_int * duration_int,
            alarm_enabled=alarm_enabled,
            is_active=True,
        )

    request.session.pop("ocr_result", None)

    return redirect("medicine_list")


def _make_default_times(count):
    defaults = ["09:00", "12:00", "18:00", "21:00"]
    return defaults[:count]


def _parse_medicine_form(request):
    dose_per_day = int(request.POST.get("dose_per_day", 1))
    duration_days = int(request.POST.get("duration_days", 1))
    meal_timing = request.POST.get("meal_timing", "after")
    alarm_enabled = request.POST.get("alarm_enabled") == "on"

    times = request.POST.getlist("alarm_times")
    times = [t for t in times if t]

    if not times:
        times = _make_default_times(dose_per_day)

    return {
        "dose_per_day": dose_per_day,
        "duration_days": duration_days,
        "meal_timing": meal_timing,
        "alarm_enabled": alarm_enabled,
        "intake_time": ",".join(times),
        "frequency": f"하루 {dose_per_day}회",
    }


@login_required
def prescription_medicine_edit(request, index):
    result = request.session.get("ocr_result")

    if not result:
        return redirect("prescription_upload")

    medicines = result.get("medicines", [])

    if index < 0 or index >= len(medicines):
        return redirect("prescription_result")

    med = medicines[index]

    if request.method == "POST":
        form_data = _parse_medicine_form(request)

        UserMedicine.objects.create(
            user=request.user,
            medicine_name=med.get("name", ""),
            ingredient_name=med.get("ingredient_name", ""),
            image=med.get("image", UserMedicine.DEFAULT_IMAGE),
            remaining_quantity=form_data["dose_per_day"] * form_data["duration_days"],
            total_quantity=form_data["dose_per_day"] * form_data["duration_days"],
            **form_data,
        )

        return redirect("medicine_list")

    context = {
        "mode": "create",
        "medicine": {
            "medicine_name": med.get("name", ""),
            "image_static_path": med.get("image", UserMedicine.DEFAULT_IMAGE),
            "dose_per_day": 3,
            "duration_days": 5,
            "meal_timing": "after",
            "alarm_enabled": False,
            "intake_times": ["09:00", "12:00", "18:00"],
        },
        "nav_active": "scan",
    }

    return render(request, "medicines/medicine_edit.html", context)


@login_required
def medicine_edit_view(request, pk):
    medicine = get_object_or_404(UserMedicine, pk=pk, user=request.user)
    medicine = apply_dummy_detail_to_medicine(medicine)

    from_page = request.GET.get("from")

    if from_page == "reminder":
        back_url = reverse("medication_reminder")
        nav_active = "reminder"
        after_save_url = reverse("medication_reminder")
    else:
        back_url = reverse("medicine_list")
        nav_active = "medicines"
        after_save_url = reverse("medicine_list")

    if request.method == "POST":
        frequency = int(request.POST.get("frequency", medicine.dose_per_day or 1))
        duration = int(request.POST.get("duration", medicine.duration_days or 1))
        meal_timing = request.POST.get("meal_timing", "after")
        alarm_enabled = request.POST.get("alarm_enabled") == "on"

        alarm_times = request.POST.getlist("alarm_times")
        alarm_times = [t for t in alarm_times if t]

        if not alarm_times:
            alarm_times = ["09:00"]

        medicine.dose_per_day = frequency
        medicine.duration_days = duration
        medicine.frequency = f"하루 {frequency}번"
        medicine.meal_timing = meal_timing
        medicine.alarm_enabled = alarm_enabled
        medicine.intake_time = ",".join(alarm_times)

        medicine.total_quantity = frequency * duration
        medicine.remaining_quantity = min(
            medicine.remaining_quantity,
            medicine.total_quantity,
        )

        medicine.save()

        return redirect(after_save_url)

    med = {
        "name": medicine.medicine_name,
"image": medicine.dummy_image_static_path,
        "frequency": medicine.dose_per_day,
        "duration": medicine.duration_days,
        "meal_timing": medicine.meal_timing,
        "alarm_enabled": medicine.alarm_enabled,
        "alarm_times": [
            t.strip() for t in medicine.intake_time.split(",") if t.strip()
        ],
    }

    return render(request, "medicines/medicine_edit_temp.html", {
        "med": med,
        "medicine": medicine,
        "mode": "edit",
        "action_url": request.get_full_path(),
        "delete_url": reverse("medicine_delete", args=[medicine.pk]),
        "back_url": back_url,
        "nav_active": nav_active,
    })

@login_required
def due_medicine_alarm_api(request):
    now = timezone.localtime()
    now_minutes = now.hour * 60 + now.minute

    due_medicines = []

    medicines = UserMedicine.objects.filter(
        user=request.user,
        is_active=True,
        alarm_enabled=True,
    )

    for medicine in medicines:
        for hour, minute in parse_intake_times(medicine.intake_time):
            medicine_minutes = hour * 60 + minute

            # 현재 시간과 복용 시간이 같으면 알림
            if now_minutes == medicine_minutes:
                due_medicines.append({
                    "id": medicine.id,
                    "name": medicine.medicine_name,
                    "image": static(medicine.image_static_path),
                    "time": f"{hour:02d}:{minute:02d}",
                    "remaining_quantity": medicine.remaining_quantity,
                    "total_quantity": medicine.total_quantity,
                })
                break

    return JsonResponse({
        "now": now.strftime("%H:%M"),
        "medicines": due_medicines,
    })

@login_required
def medicine_delete_view(request, pk):
    medicine = get_object_or_404(UserMedicine, pk=pk, user=request.user)

    if request.method == "POST":
        medicine.delete()
        return redirect("medicine_list")

    return redirect("medicine_edit", pk=pk)

@login_required
@require_POST
def update_intake_log_api(request):
    data = json.loads(request.body)

    medicine_id = data.get("medicine_id")
    intake_time = data.get("intake_time")
    status = data.get("status")

    medicine = get_object_or_404(
        UserMedicine,
        pk=medicine_id,
        user=request.user,
        is_active=True,
    )

    today = timezone.localdate()

    if status == "none":
        IntakeLog.objects.filter(
            user=request.user,
            medicine=medicine,
            intake_date=today,
            intake_time=intake_time,
        ).delete()

        return JsonResponse({
            "success": True,
            "status": None,
            "medicine_id": medicine.pk,
            "intake_time": intake_time,
        })

    if status not in ["taken", "skipped"]:
        return JsonResponse({"success": False}, status=400)

    log, created = IntakeLog.objects.update_or_create(
        user=request.user,
        medicine=medicine,
        intake_date=today,
        intake_time=intake_time,
        defaults={"status": status},
    )

    return JsonResponse({
        "success": True,
        "status": log.status,
        "medicine_id": medicine.pk,
        "intake_time": intake_time,
    })

@login_required
def medicine_detail_view(request, pk):
    """약 상세."""
    medicine = get_object_or_404(UserMedicine, pk=pk, user=request.user)

    dummy_detail = get_dummy_medicine_detail(medicine.medicine_name)

    if dummy_detail:
        medicine.manufacturer = dummy_detail["manufacturer"]
        medicine.ingredient_name = dummy_detail["ingredient_name"]
        medicine.appearance = dummy_detail["appearance"]
        medicine.mark_front = dummy_detail["mark_front"]
        medicine.mark_back = dummy_detail["mark_back"]
        medicine.color = dummy_detail["color"]
        medicine.image = dummy_detail["image"]

    context = {
        'user': request.user,
        'medicine': medicine,
        'nav_active': 'reminder',
        'back_url': reverse('medication_reminder'),
    }
    return render(request, 'medicines/medicine_detail.html', context)