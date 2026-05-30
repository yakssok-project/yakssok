console.log("reminder.js 연결됨");

document.addEventListener("DOMContentLoaded", function () {
  const calendar = document.querySelector(".reminder-calendar");
  const monthText = document.getElementById("calendarMonth");
  const weekLabel = document.getElementById("calendarWeekLabel");
  const weekWrap = document.getElementById("calendarWeek");
  const prevBtn = document.getElementById("calendarPrevBtn");
  const nextBtn = document.getElementById("calendarNextBtn");

  const selectedDateBar = document.getElementById("selectedDateBar");
  const selectedMonthDay = document.getElementById("selectedMonthDay");
  const selectedYear = document.getElementById("selectedYear");

  const weekdayNames = ["일", "월", "화", "수", "목", "금", "토"];

  function getCsrfToken() {
    return document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="))
      ?.split("=")[1];
  }

  function makeDateOnly(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  const todayDate = makeDateOnly(new Date());
  let viewDate = new Date(todayDate);
  let selectedDate = new Date(todayDate);

  function isSameDate(a, b) {
    if (!a || !b) return false;

    return (
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate()
    );
  }

  function getStartOfWeek(date) {
    const copied = new Date(date);
    copied.setDate(copied.getDate() - copied.getDay());
    return copied;
  }

  function getWeekOfMonth(date) {
    const firstDayOfMonth = new Date(date.getFullYear(), date.getMonth(), 1);
    const firstDayWeekday = firstDayOfMonth.getDay();

    return Math.ceil((date.getDate() + firstDayWeekday) / 7);
  }

  function updateSelectedDateBar() {
    if (!selectedDateBar || !selectedMonthDay || !selectedYear) return;

    selectedDateBar.hidden = false;
    selectedMonthDay.textContent = `${
      selectedDate.getMonth() + 1
    }월 ${selectedDate.getDate()}일`;
    selectedYear.textContent = selectedDate.getFullYear();
  }

  function renderCalendar() {
    if (!monthText || !weekLabel || !weekWrap) return;

    const startOfWeek = getStartOfWeek(viewDate);

    monthText.textContent = `${viewDate.getMonth() + 1}월`;
    weekLabel.textContent = `${getWeekOfMonth(viewDate)}주차`;
    weekWrap.innerHTML = "";

    for (let i = 0; i < 7; i++) {
      const current = new Date(startOfWeek);
      current.setDate(startOfWeek.getDate() + i);

      const button = document.createElement("button");
      button.type = "button";
      button.className = "calendar-day";

      if (i === 0) button.classList.add("is-sunday");
      if (i === 6) button.classList.add("is-saturday");
      if (isSameDate(current, todayDate)) button.classList.add("is-today");
      if (selectedDate && isSameDate(current, selectedDate)) {
        button.classList.add("is-selected");
      }

      button.innerHTML = `
        <span class="calendar-weekday">${weekdayNames[i]}</span>
        <span class="calendar-date">${current.getDate()}</span>
      `;

      button.addEventListener("click", function () {
        selectedDate = new Date(current);
        viewDate = new Date(current);
        renderCalendar();
      });

      weekWrap.appendChild(button);
    }

    updateSelectedDateBar();
  }

  if (prevBtn) {
    prevBtn.addEventListener("click", function () {
      viewDate.setDate(viewDate.getDate() - 7);
      renderCalendar();
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", function () {
      viewDate.setDate(viewDate.getDate() + 7);
      renderCalendar();
    });
  }

  async function saveIntakeLog(card, button) {
    const medicineId = card.dataset.medicineId;
    const intakeTime = card.dataset.intakeTime;
    const isCompleted = button.classList.contains("completed");
    const status = isCompleted ? "none" : "taken";

    if (!medicineId || !intakeTime) {
      console.error("복용 기록 저장에 필요한 데이터가 없습니다.", {
        medicineId,
        intakeTime,
        status,
      });
      return;
    }

    try {
      button.disabled = true;

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

      if (!response.ok || !data.success) {
        console.error("복용 기록 저장 실패:", data);
        return;
      }

      const image = button.querySelector(".medicine-state-image");

      if (data.status === "taken") {
        button.classList.add("completed");

        if (image) {
          image.src = "/static/medicines/img/after.png";
          image.alt = "복용 완료";
        }
      } else {
        button.classList.remove("completed");

        if (image) {
          image.src = "/static/medicines/img/before.png";
          image.alt = "복용 전";
        }
      }
    } catch (error) {
      console.error("복용 기록 저장 실패:", error);
    } finally {
      button.disabled = false;
    }
  }

  document.addEventListener("click", function (event) {
    const button = event.target.closest(".reminder-check-btn");
    if (!button) return;

    const card = button.closest(".reminder-medicine-card");
    if (!card) return;

    saveIntakeLog(card, button);
  });

  if (calendar) {
    renderCalendar();
  }
});