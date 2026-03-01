"""Серверный прокси для Yandex Geocoder HTTP API.

Клиентский ymaps.suggest() не возвращает координаты,
а ymaps.geocode() требует отдельного разрешения на ключе.
Прокси вызывает HTTP Geocoder напрямую с серверным ключом.
"""

import os
import logging

import httpx
from fastapi import APIRouter, Query

logger = logging.getLogger("staffprobot")
router = APIRouter(prefix="/api/geocode", tags=["Geocode Proxy"])

GEOCODER_URL = "https://geocode-maps.yandex.ru/1.x/"


def _get_api_key() -> str:
    return os.getenv("YANDEX_GEOCODER_API_KEY") or os.getenv("YANDEX_MAPS_API_KEY", "")


@router.get("/search")
async def geocode_search(q: str = Query(..., min_length=2, max_length=300)):
    """Прямое геокодирование: текст → координаты."""
    api_key = _get_api_key()
    if not api_key:
        return {"error": "no api key"}

    params = {
        "apikey": api_key,
        "geocode": q,
        "format": "json",
        "lang": "ru_RU",
        "results": "5",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GEOCODER_URL, params=params)
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("Geocoder HTTP error: %s", exc)
        return {"error": "geocoder unavailable"}

    data = resp.json()
    members = (
        data.get("response", {})
        .get("GeoObjectCollection", {})
        .get("featureMember", [])
    )

    results = []
    for m in members:
        obj = m.get("GeoObject", {})
        pos = obj.get("Point", {}).get("pos", "")
        parts = pos.split()
        lon = float(parts[0]) if len(parts) > 0 else 0
        lat = float(parts[1]) if len(parts) > 1 else 0
        address = (
            obj.get("metaDataProperty", {})
            .get("GeocoderMetaData", {})
            .get("text", "")
        )
        city = _extract_city(obj)
        results.append({"address": address, "lat": lat, "lon": lon, "city": city})

    return {"results": results}


@router.get("/reverse")
async def geocode_reverse(
    lat: float = Query(...), lon: float = Query(...)
):
    """Обратное геокодирование: координаты → адрес."""
    api_key = _get_api_key()
    if not api_key:
        return {"error": "no api key"}

    params = {
        "apikey": api_key,
        "geocode": f"{lon},{lat}",
        "format": "json",
        "lang": "ru_RU",
        "results": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GEOCODER_URL, params=params)
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("Geocoder reverse HTTP error: %s", exc)
        return {"error": "geocoder unavailable"}

    data = resp.json()
    members = (
        data.get("response", {})
        .get("GeoObjectCollection", {})
        .get("featureMember", [])
    )

    if not members:
        return {"found": False}

    obj = members[0].get("GeoObject", {})
    pos = obj.get("Point", {}).get("pos", "")
    parts = pos.split()
    address = (
        obj.get("metaDataProperty", {})
        .get("GeocoderMetaData", {})
        .get("text", "")
    )
    city = _extract_city(obj)

    return {
        "found": True,
        "address": address,
        "lat": lat,
        "lon": lon,
        "city": city,
    }


def _extract_city(geo_object: dict) -> str:
    try:
        components = (
            geo_object.get("metaDataProperty", {})
            .get("GeocoderMetaData", {})
            .get("Address", {})
            .get("Components", [])
        )
        for kind in ("locality", "area", "province"):
            for c in components:
                if c.get("kind") == kind:
                    return c.get("name", "")
    except Exception:
        pass
    return ""
