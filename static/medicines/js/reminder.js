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

  if (
    !calendar ||
    !monthText ||
    !weekLabel ||
    !weekWrap ||
    !prevBtn ||
    !nextBtn ||
    !selectedDateBar ||
    !selectedMonthDay ||
    !selectedYear
  ) {
    console.log("달력 요소를 찾지 못했어요.");
    return;
  }

  const weekdayNames = ["일", "월", "화", "수", "목", "금", "토"];

  function makeDateOnly(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  const todayDate = makeDateOnly(new Date());

  // 현재 보고 있는 주차 기준 날짜
  let viewDate = new Date(todayDate);

  // 선택 날짜: 처음에는 오늘로 설정
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
    copied.setDate(copied.getDate() - copied.getDay()); // 일요일 시작
    return copied;
  }

  function getWeekOfMonth(date) {
    const firstDayOfMonth = new Date(date.getFullYear(), date.getMonth(), 1);
    const firstDayWeekday = firstDayOfMonth.getDay();
    return Math.ceil((date.getDate() + firstDayWeekday) / 7);
  }

  function updateSelectedDateBar() {
    if (!selectedDate) {
      selectedDateBar.hidden = true;
      return;
    }

    selectedDateBar.hidden = false;
    selectedMonthDay.textContent = `${selectedDate.getMonth() + 1}월 ${selectedDate.getDate()}일`;
    selectedYear.textContent = selectedDate.getFullYear();
  }

  function renderCalendar() {
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

      // 오늘 날짜는 테두리 표시
      if (isSameDate(current, todayDate)) {
        button.classList.add("is-today");
      }

      // 선택 날짜가 현재 보이는 주차 안에 있을 때만 채운 원 표시
      if (selectedDate && isSameDate(current, selectedDate)) {
        button.classList.add("is-selected");
      }

      button.innerHTML = `
        <span class="calendar-weekday">${weekdayNames[i]}</span>
        <span class="calendar-date">${current.getDate()}</span>
      `;

      // 날짜를 직접 클릭했을 때만 선택 날짜 변경
      button.addEventListener("click", function () {
        selectedDate = new Date(current);
        viewDate = new Date(current);
        renderCalendar();
      });

      weekWrap.appendChild(button);
    }

    updateSelectedDateBar();
  }

  // 이전 주차 이동
  prevBtn.addEventListener("click", function () {
    viewDate.setDate(viewDate.getDate() - 7);

    // 선택 날짜는 유지한다.
    // 그래서 초록 박스 날짜는 그대로 유지됨.
    renderCalendar();
  });

  // 다음 주차 이동
  nextBtn.addEventListener("click", function () {
    viewDate.setDate(viewDate.getDate() + 7);

    // 선택 날짜는 유지한다.
    // 그래서 초록 박스 날짜는 그대로 유지됨.
    renderCalendar();
  });

  renderCalendar();
  document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".reminder-medicine-card").forEach(function (card) {
    const buttons = card.querySelectorAll(".reminder-dose-btn");

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        buttons.forEach(function (btn) {
          btn.classList.remove("is-taken", "is-skipped");
        });

        if (button.dataset.doseStatus === "taken") {
          button.classList.add("is-taken");
        }

        if (button.dataset.doseStatus === "skipped") {
          button.classList.add("is-skipped");
        }
      });
    });
  });
});
});
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".reminder-medicine-card").forEach(function (card) {
    const buttons = card.querySelectorAll(".reminder-dose-btn");

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        buttons.forEach(function (btn) {
          btn.classList.remove("is-taken", "is-skipped");
        });

        if (button.dataset.doseStatus === "taken") {
          button.classList.add("is-taken");
        }

        if (button.dataset.doseStatus === "skipped") {
          button.classList.add("is-skipped");
        }
      });
    });
  });
});