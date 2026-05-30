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

  if (!overlay || !pairEl || !noticeEl || !confirmBtn) return;

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

  if (!frequencyInput && !durationInput && !alarmToggle) return;

  let editingTimeIndex = null;
  let selectedHour = 9;
  let selectedMinute = 0;

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

    if (alarmToggle.checked) {
      alarmTimeList.hidden = false;
      renderAlarmTimes();
    }
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

  document.querySelectorAll(".time-step-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const target = btn.dataset.timeTarget;
      const delta = Number(btn.dataset.delta || 0);

      if (target === "hour") {
        selectedHour = (selectedHour + delta + 24) % 24;
      }

      if (target === "minute") {
        selectedMinute = (selectedMinute + delta + 60) % 60;
      }

      updateTimePicker();
    });
  });

  document.querySelectorAll(".period-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const period = btn.dataset.period;

      if (period === "am" && selectedHour >= 12) {
        selectedHour -= 12;
      }

      if (period === "pm" && selectedHour < 12) {
        selectedHour += 12;
      }

      updateTimePicker();
    });
  });

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

          <button type="button" class="time-open-btn" data-index="${i}">
            ›
          </button>
        </div>
        `
      );
    }
  }

  function displayHour(hour) {
    const h = hour % 12;
    return h === 0 ? 12 : h;
  }

  function updateTimePicker() {
    if (selectedHourEl) {
      selectedHourEl.textContent = String(displayHour(selectedHour)).padStart(2, "0");
    }

    if (selectedMinuteEl) {
      selectedMinuteEl.textContent = String(selectedMinute).padStart(2, "0");
    }

    document.querySelectorAll(".period-btn").forEach(function (btn) {
      btn.classList.toggle(
        "is-active",
        (btn.dataset.period === "am" && selectedHour < 12) ||
          (btn.dataset.period === "pm" && selectedHour >= 12)
      );
    });
  }
});


function getCsrfToken() {
  return document.cookie
    .split("; ")
    .find(row => row.startsWith("csrftoken="))
    ?.split("=")[1];
}

document.addEventListener("click", async function (event) {
  const button = event.target.closest(".reminder-dose-btn");
  if (!button) return;

  const card = button.closest(".reminder-medicine-card");
  if (!card) return;

  const medicineId = card.dataset.medicineId;
  const intakeTime = card.dataset.intakeTime;
  const status = button.dataset.doseStatus;

  const response = await fetch("/medicines/intake-log/update/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    body: JSON.stringify({
      medicine_id: medicineId,
      intake_time: intakeTime,
      status: status,
    }),
  });

  const data = await response.json();

  if (data.success) {
    card.querySelectorAll(".reminder-dose-btn").forEach(btn => {
      btn.classList.remove("is-selected");
    });

    button.classList.add("is-selected");
  }
});