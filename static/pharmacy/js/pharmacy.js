/**
 * 주변 약국 — Geolocation + 서버(Kakao Local) + Kakao Map JS
 */
(function () {
    'use strict';

    var root = document.getElementById('pharmacy-app');
    if (!root || root.dataset.configured !== 'true') return;

    var apiNearby = root.dataset.apiNearby;
    var jsKey = root.dataset.jsKey;
    if (!apiNearby || !jsKey) return;

    var mapEl = document.getElementById('kakao-map');
    var viewMap = document.getElementById('pharmacy-view-map');
    var viewList = document.getElementById('pharmacy-view-list');
    var listEl = document.getElementById('pharmacy-list');
    var searchInput = document.getElementById('pharmacy-search');
    var statusEl = document.getElementById('pharmacy-status');
    var btnMyLoc = document.getElementById('btn-my-location');

    var bottomCard = document.getElementById('pharmacy-bottom-card');
    var bottomClose = document.getElementById('bottom-card-close');
    var bottomName = document.getElementById('bottom-card-name');
    var bottomStatus = document.getElementById('bottom-card-status');
    var bottomCloseTime = document.getElementById('bottom-card-close-time');
    var bottomAddress = document.getElementById('bottom-card-address');
    var bottomRoute = document.getElementById('bottom-card-route');
    var bottomTel = document.getElementById('bottom-card-tel');
    var bottomImg = document.getElementById('bottom-card-img');
    var bottomPlaceholder = document.getElementById('bottom-card-placeholder');

    var allItems = [];
    var map = null;
    var markers = [];
    var userMarker = null;
    var selectedId = null;

    // 처음 화면 렌더링 시 bottom card 숨김
    if (bottomCard) {
        bottomCard.hidden = true;
    }

    function setStatus(msg, isError) {
        if (!statusEl) return;
        statusEl.textContent = msg || '';
        statusEl.classList.toggle('is-error', !!isError);
    }

    function loadScript(src) {
        return new Promise(function (resolve, reject) {
            var s = document.createElement('script');
            s.src = src;
            s.async = true;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    function ensureKakaoMaps() {
        return new Promise(function (resolve, reject) {
            function finish() {
                if (window.kakao && window.kakao.maps) {
                    kakao.maps.load(function () {
                        resolve();
                    });
                } else {
                    reject(new Error('Kakao Maps SDK 로드 실패'));
                }
            }

            if (window.kakao && window.kakao.maps) {
                finish();
                return;
            }

            var src =
                'https://dapi.kakao.com/v2/maps/sdk.js?appkey=' +
                encodeURIComponent(jsKey) +
                '&autoload=false&libraries=services';

            loadScript(src)
                .then(finish)
                .catch(function () {
                    reject(new Error('Kakao Maps SDK script 요청 실패'));
                });
        });
    }

    function kakaoDirectionsUrl(name, lat, lng) {
        return `https://map.kakao.com/link/to/${encodeURIComponent(name)},${lat},${lng}`;
    }

    function telHref(phone) {
        if (!phone) return '#';
        return 'tel:' + String(phone).replace(/\s/g, '');
    }

    function formatDistance(m) {
        if (m == null) return '';
        if (m >= 1000) return '약 ' + (m / 1000).toFixed(1) + 'km';
        return '약 ' + m + 'm';
    }

    function fillBottomCard(p) {
        if (!bottomCard) return;

        bottomName.textContent = p.name || '약국';
        bottomStatus.textContent = '영업: ' + (p.business_status || '정보 없음');
        bottomCloseTime.textContent = '영업 종료: ' + (p.closing_time || '-');
        bottomAddress.textContent = p.address || '주소 정보 없음';

        bottomRoute.href = kakaoDirectionsUrl(p.name || '약국', p.lat, p.lng);

        if (p.phone) {
            bottomTel.href = telHref(p.phone);
            bottomTel.classList.remove('btn-pharmacy-disabled');
            bottomTel.removeAttribute('aria-disabled');
        } else {
            bottomTel.href = '#';
            bottomTel.classList.add('btn-pharmacy-disabled');
            bottomTel.setAttribute('aria-disabled', 'true');
        }

        if (bottomImg) bottomImg.hidden = true;

        if (bottomPlaceholder) {
            bottomPlaceholder.hidden = false;
            bottomPlaceholder.textContent = '약';
        }
    }

    function openBottomCard(p) {
        if (!bottomCard) return;

        selectedId = p.id;
        fillBottomCard(p);
        bottomCard.hidden = false;
    }

    function closeBottomCard() {
        if (!bottomCard) return;

        bottomCard.hidden = true;
        selectedId = null;
    }

    function getFilteredItems() {
        var q = searchInput && searchInput.value ? searchInput.value.trim() : '';
        if (!q) return allItems.slice();

        var lower = q.toLowerCase();
        return allItems.filter(function (p) {
            return (p.name || '').toLowerCase().indexOf(lower) !== -1;
        });
    }

    function clearPharmacyMarkers() {
        markers.forEach(function (m) {
            m.setMap(null);
        });
        markers = [];
    }

    function renderMarkers(items) {
        if (!map || !window.kakao || !window.kakao.maps) return;

        clearPharmacyMarkers();

        var LatLng = kakao.maps.LatLng;

        items.forEach(function (p) {
            var pos = new LatLng(p.lat, p.lng);
            var marker = new kakao.maps.Marker({
                position: pos,
                map: map,
            });

            kakao.maps.event.addListener(marker, 'click', function () {
                openBottomCard(p);
            });

            markers.push(marker);
        });
    }

    function renderList() {
        var items = getFilteredItems();
        listEl.innerHTML = '';

        if (!items.length) {
            var empty = document.createElement('p');
            empty.className = 'pharmacy-status';
            empty.textContent = '검색 결과가 없습니다.';
            listEl.appendChild(empty);
            return;
        }

        items.forEach(function (p) {
            var li = document.createElement('li');
            li.className = 'pharmacy-card';

            var dist = formatDistance(p.distance_m);

            li.innerHTML =
                '<h2 class="pharmacy-card-name"></h2>' +
                '<p class="pharmacy-card-meta pharmacy-open"></p>' +
                '<p class="pharmacy-card-meta pharmacy-close-time"></p>' +
                '<p class="pharmacy-card-address"></p>' +
                (dist ? '<p class="pharmacy-card-distance"></p>' : '') +
                '<div class="pharmacy-card-actions">' +
                '<a class="btn-pharmacy btn-pharmacy-outline route-link" target="_blank" rel="noopener noreferrer">길 찾기</a>' +
                '<a class="btn-pharmacy btn-pharmacy-primary tel-link">전화하기</a>' +
                '</div>';

            li.querySelector('.pharmacy-card-name').textContent = p.name || '약국';
            li.querySelector('.pharmacy-open').textContent =
                '영업: ' + (p.business_status || '정보 없음');
            li.querySelector('.pharmacy-close-time').textContent =
                '영업 종료: ' + (p.closing_time || '-');
            li.querySelector('.pharmacy-card-address').textContent =
                p.address || '';

            if (dist) {
                li.querySelector('.pharmacy-card-distance').textContent = '거리 ' + dist;
            }

            var routeA = li.querySelector('.route-link');
            routeA.href = kakaoDirectionsUrl(p.name || '약국', p.lat, p.lng);

            var telA = li.querySelector('.tel-link');

            if (p.phone) {
                telA.href = telHref(p.phone);
            } else {
                telA.href = '#';
                telA.classList.add('btn-pharmacy-disabled');
                telA.setAttribute('aria-disabled', 'true');
            }

            li.addEventListener('click', function (e) {
                if (e.target.closest('a')) return;

                openBottomCard(p);
                switchTab('map');
            });

            listEl.appendChild(li);
        });
    }

    function refreshMarkersAndList() {
        var items = getFilteredItems();
        renderMarkers(items);
        renderList();

        if (selectedId) {
            var stillExists = items.some(function (p) {
                return p.id === selectedId;
            });

            if (!stillExists) {
                closeBottomCard();
            }
        }
    }

    function switchTab(which) {
        var tabs = root.querySelectorAll('.pharmacy-tab');

        tabs.forEach(function (t) {
            var active = t.dataset.tab === which;
            t.classList.toggle('pharmacy-tab-active', active);
            t.setAttribute('aria-selected', active ? 'true' : 'false');
        });

        if (which === 'map') {
            viewMap.hidden = false;
            viewList.hidden = true;

            if (map && map.relayout) {
                map.relayout();
            }
        } else {
            viewMap.hidden = true;
            viewList.hidden = false;
        }
    }

    function fetchNearby(lat, lng) {
        setStatus('주변 약국을 불러오는 중…', false);

        var url =
            apiNearby +
            '?lat=' +
            encodeURIComponent(lat) +
            '&lng=' +
            encodeURIComponent(lng) +
            '&radius=5000&size=15';

        return fetch(url, { credentials: 'same-origin' })
            .then(function (r) {
                return r.json().then(function (data) {
                    return { ok: r.ok, data: data };
                });
            })
            .then(function (res) {
                if (!res.ok || !res.data.ok) {
                    throw new Error(res.data.error || '약국 정보를 가져오지 못했습니다.');
                }

                allItems = res.data.items || [];

                setStatus(
                    allItems.length
                        ? '약국 ' + allItems.length + '곳을 찾았습니다.'
                        : '주변에 검색된 약국이 없습니다.',
                    false
                );

                closeBottomCard();
                refreshMarkersAndList();
            })
            .catch(function (err) {
                setStatus(err.message || '오류가 발생했습니다.', true);

                allItems = [];
                closeBottomCard();
                refreshMarkersAndList();
            });
    }

    function initMap(lat, lng) {
        if (!mapEl || !window.kakao || !window.kakao.maps) return;

        var LatLng = kakao.maps.LatLng;
        var center = new LatLng(lat, lng);

        if (!map) {
            map = new kakao.maps.Map(mapEl, {
                center: center,
                level: 5,
            });
        } else {
            map.setCenter(center);
        }

        if (!userMarker) {
            userMarker = new kakao.maps.Marker({
                position: center,
                map: map,
            });
        } else {
            userMarker.setPosition(center);
            userMarker.setMap(map);
        }

        renderMarkers(getFilteredItems());
    }

    function applyPosition(lat, lng) {
        initMap(lat, lng);
        return fetchNearby(lat, lng);
    }

    function requestLocation() {
        setStatus('현재 위치를 확인하는 중…', false);

        if (!navigator.geolocation) {
            setStatus('이 브라우저에서는 위치 정보를 사용할 수 없습니다.', true);
            return Promise.reject(new Error('geolocation 없음'));
        }

        return new Promise(function (resolve, reject) {
            navigator.geolocation.getCurrentPosition(
                function (pos) {
                    resolve({
                        lat: pos.coords.latitude,
                        lng: pos.coords.longitude,
                    });
                },
                function (err) {
                    var msg = '위치를 가져올 수 없습니다.';

                    if (err.code === 1) {
                        msg = '위치 권한이 거부되었습니다. 브라우저 설정에서 허용해주세요.';
                    }

                    setStatus(msg, true);
                    reject(err);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 60000,
                }
            );
        });
    }

    root.querySelectorAll('.pharmacy-tab').forEach(function (btn) {
        btn.addEventListener('click', function () {
            switchTab(btn.dataset.tab);
        });
    });

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            refreshMarkersAndList();
        });
    }

    if (bottomClose) {
        bottomClose.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            closeBottomCard();
        });
    }

    if (btnMyLoc) {
        btnMyLoc.addEventListener('click', function () {
            requestLocation()
                .then(function (coords) {
                    return applyPosition(coords.lat, coords.lng);
                })
                .catch(function () {});
        });
    }

    ensureKakaoMaps()
        .then(function () {
            return requestLocation();
        })
        .then(function (coords) {
            return applyPosition(coords.lat, coords.lng);
        })
        .catch(function () {
            if (window.kakao && window.kakao.maps) {
                var seoul = {
                    lat: 37.5665,
                    lng: 126.978,
                };

                setStatus('위치를 알 수 없어 서울 시청 근처를 표시합니다.', true);
                applyPosition(seoul.lat, seoul.lng);
            }
        });
})();