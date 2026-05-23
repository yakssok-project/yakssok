/**
 * DDI 위험 약 조합 경고 팝업 (medicine_list.html)
 * - 위험한 약 2개: 이름 + 이미지 + 간단 주의 문구
 * - 더 알아보기: 금기 사유(contraindication_reason) 상세
 * - 약사에게 문의하기: 전화 연결
 * - 확인: 다음 경고 표시 또는 팝업 종료
 */
(function () {
    'use strict';

    const noticeEl = document.getElementById('ddi-short-notice');

    const dataEl = document.getElementById('ddi-warnings-data');
    if (!dataEl) return;

    let warnings;
    try {
        warnings = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('DDI 경고 데이터를 읽을 수 없습니다.', e);
        return;
    }

    if (!Array.isArray(warnings) || warnings.length === 0) return;

    const overlay = document.getElementById('ddi-modal-overlay');
    const pairEl = document.getElementById('ddi-medicine-pair');
    const confirmBtn = document.getElementById('ddi-confirm-btn');

    if (!overlay || !pairEl || !noticeEl || !confirmBtn) {
        console.error('DDI 팝업에 필요한 DOM 요소가 없습니다.');
        return;
    }

    let currentIndex = 0;
    let bodyScrollLocked = false;

    function lockBodyScroll(lock) {
        if (lock && !bodyScrollLocked) {
            document.body.style.overflow = 'hidden';
            bodyScrollLocked = true;
        } else if (!lock && bodyScrollLocked) {
            document.body.style.overflow = '';
            bodyScrollLocked = false;
        }
    }

    function renderPair(warning) {
        const m1 = warning.medicine_1 || {};
        const m2 = warning.medicine_2 || {};

        pairEl.replaceChildren();

        function appendMedItem(container, med) {
            const wrap = document.createElement('div');
            wrap.className = 'ddi-med-item';
            const img = document.createElement('img');
            img.alt = med.name || '약';
            if (med.image) {
                img.src = String(med.image);
            }
            const caption = document.createElement('p');
            caption.textContent = med.name || '약';
            wrap.appendChild(img);
            wrap.appendChild(caption);
            container.appendChild(wrap);
        }

        appendMedItem(pairEl, m1);

        const plus = document.createElement('span');
        plus.className = 'ddi-med-plus';
        plus.setAttribute('aria-hidden', 'true');
        plus.textContent = '+';
        pairEl.appendChild(plus);

        appendMedItem(pairEl, m2);

        noticeEl.textContent =
            warning.easy_reason ||
            warning.reason ||
            '함께 복용할 때 주의가 필요해요. 복용 전 약사나 의사에게 확인해주세요.';
    }

    function showMainModal(show) {
        overlay.hidden = !show;
        lockBodyScroll(show && detailOverlay.hidden);
        if (!show) stopTTS();
        if (show) confirmBtn.focus();
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

    confirmBtn.addEventListener('click', function () {
        showWarning(currentIndex + 1);
    });

    document.addEventListener('keydown', function onKey(e) {
        if (e.key !== 'Escape') return;

        if (!overlay.hidden) {
            showWarning(currentIndex + 1);
            e.preventDefault();
        }
    });

    // 배경 클릭 시에는 닫지 않음(실수로 건너뛰기 방지). 확인 버튼으로만 진행.

    document.addEventListener('keydown', function onKey(e) {
        if (e.key !== 'Escape') return;
        if (!detailOverlay.hidden) {
            showDetailModal(false);
            e.preventDefault();
            return;
        }
        if (!overlay.hidden) {
            showWarning(currentIndex + 1);
            e.preventDefault();
        }
    });

    /* ── TTS ── */
    const ttsBtn = document.getElementById('ddi-tts-btn');

    function stopTTS() {
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        if (ttsBtn) ttsBtn.classList.remove('speaking');
    }

    if (ttsBtn) {
        ttsBtn.addEventListener('click', function () {
            if (!window.speechSynthesis) {
                alert('이 브라우저는 음성 읽기를 지원하지 않습니다.');
                return;
            }

            // 이미 읽는 중이면 중지
            if (window.speechSynthesis.speaking) {
                stopTTS();
                return;
            }

            const text = noticeEl ? noticeEl.textContent.trim() : '';
            if (!text) return;

            const utter = new SpeechSynthesisUtterance(text);
            utter.lang = 'ko-KR';
            utter.rate = 0.95;

            utter.onstart = () => ttsBtn.classList.add('speaking');
            utter.onend = () => ttsBtn.classList.remove('speaking');
            utter.onerror = () => ttsBtn.classList.remove('speaking');

            window.speechSynthesis.speak(utter);
        });
    }

    showWarning(0);
})();