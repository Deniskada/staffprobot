// Общий модуль работы с Яндекс.Картой для выбора адреса.
// Карта — ymaps, всё остальное — серверный прокси /api/geocode/.

window.SPAddressMap = (function () {
  var map = null;
  var placemark = null;
  var config = null;
  var suggestTimer = null;

  function ensureYMapsReady(callback) {
    if (typeof ymaps === "undefined") {
      console.error("Yandex Maps API не загружен");
      return;
    }
    ymaps.ready(callback);
  }

  function init(userConfig) {
    config = Object.assign(
      {
        searchInputId: "spAddressSearchInput",
        suggestionsId: "spAddressSuggestions",
        mapContainerId: "spAddressMap",
        initialLat: 55.751244,
        initialLon: 37.618423,
        zoom: 10,
        onAddressSelected: null,
      },
      userConfig || {}
    );

    var input = document.getElementById(config.searchInputId);
    var suggestions = document.getElementById(config.suggestionsId);
    var mapContainer = document.getElementById(config.mapContainerId);

    if (!input || !suggestions || !mapContainer) {
      console.warn("SPAddressMap: элементы не найдены, инициализация пропущена");
      return;
    }

    ensureYMapsReady(function () {
      map = new ymaps.Map(config.mapContainerId, {
        center: [config.initialLat, config.initialLon],
        zoom: config.zoom,
        controls: ["zoomControl", "fullscreenControl"],
      });

      placemark = new ymaps.Placemark(
        map.getCenter(),
        {},
        { draggable: true, preset: "islands#redDotIcon" }
      );
      map.geoObjects.add(placemark);

      placemark.events.add("dragend", function () {
        var coords = placemark.geometry.getCoordinates();
        reverseGeocode(coords);
      });

      map.events.add("click", function (e) {
        var coords = e.get("coords");
        if (placemark) {
          placemark.geometry.setCoordinates(coords);
        }
        reverseGeocode(coords);
      });
    });

    input.addEventListener("input", function () {
      var query = this.value.trim();
      if (suggestTimer) clearTimeout(suggestTimer);
      if (!query) {
        suggestions.innerHTML =
          '<div class="list-group-item text-muted small">Введите адрес, чтобы увидеть подсказки.</div>';
        return;
      }
      suggestTimer = setTimeout(function () {
        searchByQuery(query);
      }, 400);
    });
  }

  // Подсказки через серверный прокси /api/geocode/search
  function searchByQuery(query) {
    var suggestions = document.getElementById(config.suggestionsId);
    if (!suggestions) return;

    suggestions.innerHTML =
      '<div class="list-group-item text-muted small">Поиск адреса...</div>';

    fetch("/api/geocode/search?q=" + encodeURIComponent(query))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error || !data.results || data.results.length === 0) {
          suggestions.innerHTML =
            '<div class="list-group-item text-muted small">Ничего не найдено. Попробуйте уточнить запрос.</div>';
          return;
        }

        suggestions.innerHTML = "";
        data.results.forEach(function (item) {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "list-group-item list-group-item-action small";
          btn.textContent = item.address;
          btn.onclick = function () {
            selectResult(item);
          };
          suggestions.appendChild(btn);
        });
      })
      .catch(function (err) {
        console.warn("Address search error:", err);
        suggestions.innerHTML =
          '<div class="list-group-item text-warning small">' +
          '<i class="bi bi-exclamation-triangle me-1"></i>' +
          "Ошибка поиска адреса.</div>";
      });
  }

  // Выбор результата из подсказок (координаты уже есть)
  function selectResult(item) {
    var input = document.getElementById(config.searchInputId);
    var suggestions = document.getElementById(config.suggestionsId);
    var coords = [item.lat, item.lon];

    if (input) input.value = item.address;

    if (map && placemark) {
      placemark.geometry.setCoordinates(coords);
      map.setCenter(coords, 16, { duration: 300 });
    }

    if (suggestions) {
      suggestions.innerHTML =
        '<div class="list-group-item small text-success">Адрес выбран: ' +
        item.address + "</div>";
    }

    if (typeof config.onAddressSelected === "function") {
      config.onAddressSelected({
        full_address: item.address,
        lat: item.lat,
        lon: item.lon,
        city: item.city || "",
      });
    }
  }

  // Обратное геокодирование через серверный прокси
  function reverseGeocode(coords) {
    var suggestions = document.getElementById(config.suggestionsId);
    var input = document.getElementById(config.searchInputId);

    if (suggestions) {
      suggestions.innerHTML =
        '<div class="list-group-item text-muted small">Определяем адрес по точке на карте...</div>';
    }

    fetch("/api/geocode/reverse?lat=" + coords[0] + "&lon=" + coords[1])
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error || !data.found) {
          if (suggestions) {
            suggestions.innerHTML =
              '<div class="list-group-item text-muted small">' +
              "Не удалось определить адрес. Введите вручную.</div>";
          }
          return;
        }

        if (input) input.value = data.address;

        if (suggestions) {
          suggestions.innerHTML =
            '<div class="list-group-item small text-success">Адрес выбран: ' +
            data.address + "</div>";
        }

        if (typeof config.onAddressSelected === "function") {
          config.onAddressSelected({
            full_address: data.address,
            lat: data.lat,
            lon: data.lon,
            city: data.city || "",
          });
        }
      })
      .catch(function (err) {
        console.warn("Reverse geocode proxy error:", err);
        if (suggestions) {
          suggestions.innerHTML =
            '<div class="list-group-item text-warning small">' +
            '<i class="bi bi-exclamation-triangle me-1"></i>' +
            "Ошибка определения адреса.</div>";
        }
      });
  }

  function setCenterByQuery(query) {
    if (!query) return;

    fetch("/api/geocode/search?q=" + encodeURIComponent(query))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error || !data.results || data.results.length === 0) return;
        var best = data.results[0];
        var coords = [best.lat, best.lon];
        ensureYMapsReady(function () {
          if (map && placemark) {
            placemark.geometry.setCoordinates(coords);
            map.setCenter(coords, 16, { duration: 300 });
          }
        });
      })
      .catch(function (err) {
        console.warn("setCenterByQuery error:", err);
      });
  }

  return {
    init: init,
    setCenterByQuery: setCenterByQuery,
  };
})();
