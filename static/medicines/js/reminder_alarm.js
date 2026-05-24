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
    const visibleCount = 3;
    const exitDuration = 280;
    const enterDuration = 240;
  
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
  
          /*
            핵심 수정:
            기존에 보이던 카드는 다시 등장 애니메이션을 주지 않음.
            새로 올라오는 카드만 is-entering 적용.
          */
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
  
    function showAlarm(timeText) {
      alarmTime.textContent = timeText;
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
      snoozeAlarm(alarmTime.textContent.trim() || "11:50");
    });
  
    window.YakssokAlarm = {
      show: showAlarm,
      hide: hideAlarm,
      snooze: snoozeAlarm,
      render: renderVisibleCards
    };
  
    renderVisibleCards();
  });