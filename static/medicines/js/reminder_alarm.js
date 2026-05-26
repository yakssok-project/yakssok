document.addEventListener("DOMContentLoaded", function () {
  const overlay = document.getElementById("yakssokAlarmOverlay");
  const alarmTime = document.getElementById("yakssokAlarmTime");
  const alarmCardList = document.getElementById("yakssokAlarmCardList");
  const allTakenBtn = document.getElementById("yakssokAlarmAllTakenBtn");
  const snoozeBtn = document.getElementById("yakssokAlarmSnoozeBtn");

  if (!overlay || !alarmTime || !alarmCardList || !allTakenBtn || !snoozeBtn) {
    return;
  }

  let snoozeTimer = null;
  let lastAlarmKey = null;

  const visibleCount = 3;
  const exitDuration = 280;
  const enterDuration = 240;
  const alarmCheckInterval = 30000;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function createAlarmCard(medicine) {
    const id = escapeHtml(medicine.id);
    const name = escapeHtml(medicine.name || "복용할 약");
    const image = escapeHtml(medicine.image || "");

    return `
      <article class="alarm-card" data-alarm-card data-medicine-id="${id}">
        <div class="alarm-card-image">
          ${
            image
              ? `<img src="${image}" alt="${name}" />`
              : `<div class="alarm-card-image-placeholder"></div>`
          }
        </div>

        <div class="alarm-card-content">
          <span class="alarm-card-badge">처방약</span>
          <p class="alarm-card-name">${name}</p>

          <div class="alarm-card-progress">
            <span></span>
          </div>
        </div>

        <button type="button" class="alarm-card-arrow" aria-label="약 상세 보기">
          &gt;
        </button>

        <div class="alarm-card-actions">
          <button type="button" data-alarm-action="taken">복용함</button>
          <button type="button" data-alarm-action="skip">복용안함</button>
        </div>
      </article>
    `;
  }

  function getCards() {
    return Array.from(alarmCardList.querySelectorAll("[data-alarm-card]"));
  }

  function getRemainingCards() {
    return getCards().filter(function (card) {
      return !card.dataset.done;
    });
  }

  function renderVisibleCards() {
    const cards = getCards();
    const remainingCards = getRemainingCards();
    const nextVisibleCards = remainingCards.slice(0, visibleCount);

    cards.forEach(function (card) {
      const shouldBeVisible = nextVisibleCards.includes(card);
      const wasVisible = !card.classList.contains("is-hidden");

      card.classList.remove("is-exiting");

      if (shouldBeVisible) {
        card.classList.remove("is-hidden");

        if (!wasVisible) {
          card.classList.add("is-entering");

          setTimeout(function () {
            card.classList.remove("is-entering");
          }, enterDuration);
        }
      } else {
        card.classList.add("is-hidden");
        card.classList.remove("is-entering");
      }
    });

    if (remainingCards.length === 0) {
      hideAlarm();
    }
  }

  function animateAndRemoveCard(card) {
    if (!card || card.classList.contains("is-exiting")) return;

    card.classList.add("is-exiting");

    setTimeout(function () {
      card.dataset.done = "true";
      renderVisibleCards();
    }, exitDuration);
  }

  function animateAndRemoveVisibleCards() {
    const visibleCards = getRemainingCards()
      .slice(0, visibleCount)
      .filter(function (card) {
        return !card.classList.contains("is-hidden");
      });

    if (visibleCards.length === 0) {
      hideAlarm();
      return;
    }

    visibleCards.forEach(function (card) {
      card.classList.add("is-exiting");
    });

    setTimeout(function () {
      visibleCards.forEach(function (card) {
        card.dataset.done = "true";
      });

      renderVisibleCards();
    }, exitDuration);
  }

  function showAlarm(payload) {
    const timeText =
      typeof payload === "string" ? payload : payload?.time || "복용 시간";

    const medicines =
      typeof payload === "object" && Array.isArray(payload.medicines)
        ? payload.medicines
        : [];

    alarmTime.textContent = timeText;

    if (medicines.length > 0) {
      alarmCardList.innerHTML = medicines.map(createAlarmCard).join("");
    }

    overlay.hidden = false;
    renderVisibleCards();
  }

  function hideAlarm() {
    overlay.hidden = true;
  }

  function snoozeAlarm(timeText) {
    hideAlarm();

    if (snoozeTimer) {
      clearTimeout(snoozeTimer);
    }

    snoozeTimer = setTimeout(function () {
      showAlarm(timeText);
    }, 15 * 60 * 1000);
  }

  async function checkMedicineAlarm() {
    try {
      const response = await fetch("/medicines/alarm/due/");

      if (!response.ok) {
        throw new Error("알림 API 요청 실패");
      }

      const data = await response.json();

      if (!data.medicines || data.medicines.length === 0) {
        return;
      }

      const alarmKey =
        data.now + "-" + data.medicines.map(function (medicine) {
          return medicine.id;
        }).join(",");

      if (lastAlarmKey === alarmKey) {
        return;
      }

      lastAlarmKey = alarmKey;

      showAlarm({
        time: data.now,
        medicines: data.medicines,
      });
    } catch (error) {
      console.error("복약 알림 확인 실패:", error);
    }
  }

  alarmCardList.addEventListener("click", function (event) {
    const doseButton = event.target.closest("[data-alarm-action]");
    if (!doseButton) return;

    const card = doseButton.closest("[data-alarm-card]");
    if (!card) return;

    animateAndRemoveCard(card);
  });

  allTakenBtn.addEventListener("click", function () {
    animateAndRemoveVisibleCards();
  });

  snoozeBtn.addEventListener("click", function () {
    snoozeAlarm(alarmTime.textContent.trim() || "복용 시간");
  });

  window.YakssokAlarm = {
    show: showAlarm,
    hide: hideAlarm,
    snooze: snoozeAlarm,
    render: renderVisibleCards,
  };

  renderVisibleCards();
  checkMedicineAlarm();
  setInterval(checkMedicineAlarm, alarmCheckInterval);
});