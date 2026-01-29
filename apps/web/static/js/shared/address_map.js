// Общий модуль работы с Яндекс.Картой для выбора адреса.
// Используется на страницах профилей и объектов владельца.

window.SPAddressMap = (function () {
  let map = null;
  let placemark = null;
  let config = null;
  let geocodeTimer = null;

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

    const input = document.getElementById(config.searchInputId);
    const suggestions = document.getElementById(config.suggestionsId);
    const mapContainer = document.getElementById(config.mapContainerId);

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
        const coords = placemark.getCoordinates();
        reverseGeocode(coords);
      });

      map.events.add("click", function (e) {
        const coords = e.get("coords");
        if (placemark) {
          placemark.geometry.setCoordinates(coords);
        }
        reverseGeocode(coords);
      });
    });

    input.addEventListener("input", function () {
      const query = this.value.trim();
      if (geocodeTimer) {
        clearTimeout(geocodeTimer);
      }
      if (!query) {
        suggestions.innerHTML =
          '<div class="list-group-item text-muted small">Введите адрес, чтобы увидеть подсказки.</div>';
        return;
      }
      geocodeTimer = setTimeout(function () {
        searchByQuery(query);
      }, 400);
    });
  }

  function searchByQuery(query) {
    const suggestions = document.getElementById(config.suggestionsId);
    if (!suggestions) return;

    suggestions.innerHTML =
      '<div class="list-group-item text-muted small">Поиск адреса...</div>';

    ymaps
      .geocode(query, { results: 5 })
      .then(function (res) {
        const geoObjects = res.geoObjects;
        if (!geoObjects || geoObjects.getLength() === 0) {
          suggestions.innerHTML =
            '<div class="list-group-item text-muted small">Ничего не найдено. Попробуйте уточнить запрос.</div>';
          return;
        }

        suggestions.innerHTML = "";
        geoObjects.each(function (geoObject) {
          const addressLine = geoObject.getAddressLine
            ? geoObject.getAddressLine()
            : geoObject.getProperty && geoObject.getProperty("name")
            ? geoObject.getProperty("name")
            : geoObject.properties.get("text") || "";

          const coords = geoObject.geometry.getCoordinates();
          const item = document.createElement("button");
          item.type = "button";
          item.className = "list-group-item list-group-item-action small";
          item.textContent = addressLine;
          item.onclick = function () {
            applySelection(coords, geoObject);
          };
          suggestions.appendChild(item);
        });
      })
      .catch(function (e) {
        console.error("Yandex geocode error", e);
        suggestions.innerHTML =
          '<div class="list-group-item text-danger small">Ошибка поиска адреса</div>';
      });
  }

  function reverseGeocode(coords) {
    const suggestions = document.getElementById(config.suggestionsId);
    if (suggestions) {
      suggestions.innerHTML =
        '<div class="list-group-item text-muted small">Определяем адрес по точке на карте...</div>';
    }
    ymaps
      .geocode(coords, { results: 1 })
      .then(function (res) {
        const geoObject = res.geoObjects.get(0);
        if (!geoObject) {
          if (suggestions) {
            suggestions.innerHTML =
              '<div class="list-group-item text-muted small">Не удалось определить адрес для выбранной точки.</div>';
          }
          return;
        }

        applySelection(coords, geoObject);
      })
      .catch(function (e) {
        console.error("Yandex reverse geocode error", e);
        if (suggestions) {
          suggestions.innerHTML =
            '<div class="list-group-item text-danger small">Ошибка определения адреса</div>';
        }
      });
  }

  function extractCity(geoObject) {
    try {
      const meta = geoObject.getGeocoderMetaData();
      const components = meta.Address.Components || [];
      const locality = components.find(function (c) {
        return c.kind === "locality" || c.kind === "province" || c.kind === "area";
      });
      return locality ? locality.name : "";
    } catch (e) {
      return "";
    }
  }

  function applySelection(coords, geoObject) {
    const [lat, lon] = coords;
    const input = document.getElementById(config.searchInputId);
    const suggestions = document.getElementById(config.suggestionsId);

    const addressLine = geoObject.getAddressLine
      ? geoObject.getAddressLine()
      : geoObject.getProperty && geoObject.getProperty("name")
      ? geoObject.getProperty("name")
      : geoObject.properties.get("text") || "";

    if (input) {
      input.value = addressLine;
    }
    if (suggestions) {
      suggestions.innerHTML =
        '<div class="list-group-item small text-success">Адрес выбран: ' +
        addressLine +
        "</div>";
    }

    if (map && placemark) {
      placemark.geometry.setCoordinates([lat, lon]);
      map.setCenter([lat, lon], 16, { duration: 300 });
    }

    if (typeof config.onAddressSelected === "function") {
      config.onAddressSelected({
        full_address: addressLine,
        lat: lat,
        lon: lon,
        city: extractCity(geoObject),
      });
    }
  }

  function setCenterByQuery(query) {
    if (!query) {
      return;
    }
    ensureYMapsReady(function () {
      ymaps
        .geocode(query, { results: 1 })
        .then(function (res) {
          const geoObject = res.geoObjects.get(0);
          if (!geoObject) {
            return;
          }
          const coords = geoObject.geometry.getCoordinates();
          if (map && placemark) {
            placemark.geometry.setCoordinates(coords);
            map.setCenter(coords, 16, { duration: 300 });
          }
        })
        .catch(function (e) {
          console.error("Yandex setCenterByQuery error", e);
        });
    });
  }

  return {
    init: init,
    setCenterByQuery: setCenterByQuery,
  };
})();

