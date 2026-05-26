/**
 * DDI 위험 약 조합 경고 팝업 (medicine_list.html)
 * - 위험한 약 2개: 이름 + 이미지 + 간단 주의 문구
 * - 더 알아보기: 금기 사유(contraindication_reason) 상세
 * - 약사에게 문의하기: 전화 연결
 * - 확인: 다음 경고 표시 또는 팝업 종료
 */
/**
 * DDI 위험 약 조합 경고 팝업 (medicine_list.html)
 */
(function () {
  "use strict";

  const noticeEl = document.getElementById("ddi-short-notice");
  const dataEl = document.getElementById("ddi-warnings-data");

  if (!dataEl) return;

  let warnings;
  try {
    warnings = JSON.parse(dataEl.textContent);
  } catch (e) {
    console.error("DDI 경고 데이터를 읽을 수 없습니다.", e);
    return;
  }

  if (!Array.isArray(warnings) || warnings.length === 0) return;

  const overlay = document.getElementById("ddi-modal-overlay");
  const pairEl = document.getElementById("ddi-medicine-pair");
  const confirmBtn = document.getElementById("ddi-confirm-btn");
  const ttsBtn = document.getElementById("ddi-tts-btn");

  if (!overlay || !pairEl || !noticeEl || !confirmBtn) {
    console.error("DDI 팝업에 필요한 DOM 요소가 없습니다.");
    return;
  }

  let currentIndex = 0;
  let bodyScrollLocked = false;

  function lockBodyScroll(lock) {
    if (lock && !bodyScrollLocked) {
      document.body.style.overflow = "hidden";
      bodyScrollLocked = true;
    } else if (!lock && bodyScrollLocked) {
      document.body.style.overflow = "";
      bodyScrollLocked = false;
    }
  }

  function stopTTS() {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    if (ttsBtn) {
      ttsBtn.classList.remove("speaking");
    }
  }

  function appendMedItem(container, med) {
    const wrap = document.createElement("div");
    wrap.className = "ddi-med-item";

    const img = document.createElement("img");
    img.alt = med.name || "약";

    if (med.image) {
      img.src = String(med.image);
    }

    const caption = document.createElement("p");
    caption.textContent = med.name || "약";

    wrap.appendChild(img);
    wrap.appendChild(caption);
    container.appendChild(wrap);
  }

  function renderPair(warning) {
    const m1 = warning.medicine_1 || {};
    const m2 = warning.medicine_2 || {};

    pairEl.replaceChildren();

    appendMedItem(pairEl, m1);

    const plus = document.createElement("span");
    plus.className = "ddi-med-plus";
    plus.setAttribute("aria-hidden", "true");
    plus.textContent = "+";
    pairEl.appendChild(plus);

    appendMedItem(pairEl, m2);

    noticeEl.textContent =
      warning.easy_reason ||
      warning.reason ||
      "함께 복용할 때 주의가 필요해요. 복용 전 약사나 의사에게 확인해주세요.";
  }

  function showMainModal(show) {
    overlay.hidden = !show;
    lockBodyScroll(show);

    if (!show) {
      stopTTS();
    }

    if (show) {
      confirmBtn.focus();
    }
  }

  function showWarning(index) {
    if (index >= warnings.length) {
      showMainModal(false);
      lockBodyScroll(false);
      return;
    }

    currentIndex = index;
    renderPair(warnings[index]);
    showMainModal(true);
  }

  confirmBtn.addEventListener("click", function () {
    showWarning(currentIndex + 1);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;

    if (!overlay.hidden) {
      showWarning(currentIndex + 1);
      e.preventDefault();
    }
  });

  if (ttsBtn) {
    ttsBtn.addEventListener("click", function () {
      if (!window.speechSynthesis) {
        alert("이 브라우저는 음성 읽기를 지원하지 않습니다.");
        return;
      }

      if (window.speechSynthesis.speaking) {
        stopTTS();
        return;
      }

      const text = noticeEl ? noticeEl.textContent.trim() : "";
      if (!text) return;

      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = "ko-KR";
      utter.rate = 0.95;

      utter.onstart = function () {
        ttsBtn.classList.add("speaking");
      };

      utter.onend = function () {
        ttsBtn.classList.remove("speaking");
      };

      utter.onerror = function () {
        ttsBtn.classList.remove("speaking");
      };

      window.speechSynthesis.speak(utter);
    });
  }

  showWarning(0);
})();

/**
 * 약 정보 수정 화면 (medicine_edit_temp.html)
 */
document.addEventListener("DOMContentLoaded", function () {
  const frequencyInput = document.getElementById("frequency");
  const durationInput = document.getElementById("duration");
  const alarmToggle = document.getElementById("alarm_enabled");
  const alarmTimeList = document.getElementById("alarm_time_list");

  const editForm = document.getElementById("medicine_edit_form");
  const timeEditPanel = document.getElementById("time_edit_panel");
  const timeSaveBtn = document.getElementById("time_save_btn");

  const selectedHourEl = document.getElementById("selected_hour");
  const selectedMinuteEl = document.getElementById("selected_minute");
  const pickerBox = document.querySelector(".time-picker-box");

  if (!frequencyInput && !durationInput && !alarmToggle) return;

  let editingTimeIndex = null;
  let selectedHour = 9;
  let selectedMinute = 0;

  let dragStartY = null;
  let isDragging = false;

  const defaultTimes = ["09:00", "12:00", "18:00", "21:00"];

  document.querySelectorAll(".count-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const input = document.getElementById(btn.dataset.target);
      if (!input) return;

      const delta = Number(btn.dataset.delta || 0);
      const current = Number(input.value) || 0;
      const next = Math.max(1, current + delta);

      input.value = next;

      if (
        btn.dataset.target === "frequency" &&
        alarmToggle &&
        alarmToggle.checked
      ) {
        renderAlarmTimes();
      }
    });
  });

  if (alarmToggle && alarmTimeList) {
    alarmToggle.addEventListener("change", function () {
      alarmTimeList.hidden = !alarmToggle.checked;

      if (alarmToggle.checked) {
        renderAlarmTimes();
      } else {
        alarmTimeList.innerHTML = "";
      }
    });
  }

  if (alarmTimeList) {
    alarmTimeList.addEventListener("click", function (e) {
      const btn = e.target.closest(".time-open-btn");
      if (!btn) return;

      editingTimeIndex = Number(btn.dataset.index);

      const timeInputs = alarmTimeList.querySelectorAll(
        'input[name="alarm_times"]'
      );
      const timeInput = timeInputs[editingTimeIndex];
      if (!timeInput) return;

      const time = timeInput.value || "09:00";
      const [hour, minute] = time.split(":").map(Number);

      selectedHour = Number.isNaN(hour) ? 9 : hour;
      selectedMinute = Number.isNaN(minute) ? 0 : minute;

      updateTimePicker();

      editForm.hidden = true;
      timeEditPanel.hidden = false;
    });
  }

  if (pickerBox) {
    pickerBox.addEventListener("pointerdown", function (e) {
      dragStartY = e.clientY;
      isDragging = true;
      pickerBox.setPointerCapture(e.pointerId);
    });

    pickerBox.addEventListener("pointermove", function (e) {
      if (!isDragging || dragStartY === null) return;

      const diff = dragStartY - e.clientY;

      if (Math.abs(diff) < 28) return;

      if (diff > 0) {
        selectedHour = selectedHour === 23 ? 0 : selectedHour + 1;
      } else {
        selectedHour = selectedHour === 0 ? 23 : selectedHour - 1;
      }

      dragStartY = e.clientY;
      updateTimePicker();
    });

    pickerBox.addEventListener("pointerup", function () {
      isDragging = false;
      dragStartY = null;
    });

    pickerBox.addEventListener("pointercancel", function () {
      isDragging = false;
      dragStartY = null;
    });
  }

  if (selectedMinuteEl) {
    selectedMinuteEl.addEventListener("wheel", function (e) {
      e.preventDefault();

      if (e.deltaY < 0) {
        selectedMinute = selectedMinute === 59 ? 0 : selectedMinute + 1;
      } else {
        selectedMinute = selectedMinute === 0 ? 59 : selectedMinute - 1;
      }

      updateTimePicker();
    });
  }

  if (selectedHourEl) {
    selectedHourEl.addEventListener("wheel", function (e) {
      e.preventDefault();

      if (e.deltaY < 0) {
        selectedHour = selectedHour === 23 ? 0 : selectedHour + 1;
      } else {
        selectedHour = selectedHour === 0 ? 23 : selectedHour - 1;
      }

      updateTimePicker();
    });
  }

  if (timeSaveBtn) {
    timeSaveBtn.addEventListener("click", function () {
      if (editingTimeIndex === null || !alarmTimeList) return;

      const newTime = `${String(selectedHour).padStart(2, "0")}:${String(
        selectedMinute
      ).padStart(2, "0")}`;

      const cards = alarmTimeList.querySelectorAll(".alarm-time-card");
      const targetCard = cards[editingTimeIndex];
      if (!targetCard) return;

      targetCard.querySelector("strong").textContent = newTime;
      targetCard.querySelector('input[name="alarm_times"]').value = newTime;

      timeEditPanel.hidden = true;
      editForm.hidden = false;
    });
  }

  function renderAlarmTimes() {
    if (!frequencyInput || !alarmTimeList) return;

    const count = Number(frequencyInput.value || 1);
    alarmTimeList.innerHTML = "";

    for (let i = 0; i < count; i++) {
      const time = defaultTimes[i] || "09:00";

      alarmTimeList.insertAdjacentHTML(
        "beforeend",
        `
        <div class="alarm-time-card">
          <div>
            <span>${i + 1}회차</span>
            <strong>${time}</strong>
          </div>
          <input type="hidden" name="alarm_times" value="${time}">
          <button type="button" class="time-open-btn" data-index="${i}">›</button>
        </div>
        `
      );
    }
  }

  function periodLabel(hour) {
    return hour < 12 ? "오전" : "오후";
  }

  function updateTimePicker() {
    const prevHour = selectedHour === 0 ? 23 : selectedHour - 1;
    const nextHour = selectedHour === 23 ? 0 : selectedHour + 1;

    const prevMinute = selectedMinute === 0 ? 59 : selectedMinute - 1;
    const nextMinute = selectedMinute === 59 ? 0 : selectedMinute + 1;

    document.getElementById("period_text").textContent =
      periodLabel(selectedHour);

    document.getElementById("selected_hour").textContent = String(
      selectedHour
    ).padStart(2, "0");

    document.getElementById("selected_minute").textContent = String(
      selectedMinute
    ).padStart(2, "0");

    document.getElementById("prev_hour").textContent = String(prevHour).padStart(
      2,
      "0"
    );

    document.getElementById("prev_minute").textContent = String(
      prevMinute
    ).padStart(2, "0");

    document.getElementById("next_hour").textContent = String(nextHour).padStart(
      2,
      "0"
    );

    document.getElementById("next_minute").textContent = String(
      nextMinute
    ).padStart(2, "0");
  }
});