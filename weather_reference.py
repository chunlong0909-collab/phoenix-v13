"""透明的比賽天氣參考；不改變模型expected goals。"""
from __future__ import annotations
import os
from datetime import datetime
import requests


def _label(temp, humidity, rain, wind):
    if temp is not None and temp > 28 and humidity is not None and humidity > 75:
        return "高溫潮濕，細球機率上升"
    if rain is not None and rain > 5:
        return "降雨較大，僅供參考"
    if wind is not None and wind >= 40:
        return "風勢較強，僅供參考"
    return "一般天氣，僅供參考"


def get_match_weather(city="Dubai", country="UAE", match_datetime="2026-10-27T20:00:00", timeout=12):
    """回傳可追溯天氣資料；資料不足時不虛構數值。"""
    target = datetime.fromisoformat(match_datetime)
    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "").strip()
    if api_key:
        try:
            r = requests.get("https://api.openweathermap.org/data/2.5/forecast", params={"q": f"{city},{country}", "appid": api_key, "units": "metric", "lang": "en"}, timeout=timeout)
            r.raise_for_status()
            items = r.json().get("list", [])
            item = min(items, key=lambda x: abs(datetime.fromtimestamp(x["dt"]) - target))
            main, wind = item.get("main", {}), item.get("wind", {})
            temp, humidity, rain = main.get("temp"), main.get("humidity"), (item.get("rain") or {}).get("3h", 0)
            return {"status": "ok", "completeness": "已獲取", "source": "OpenWeatherMap", "city": city, "temp_c": temp, "humidity": humidity, "wind_kmh": (wind.get("speed", 0) or 0) * 3.6, "rain_mm": rain, "label": _label(temp, humidity, rain, wind.get("speed", 0) * 3.6), "target": match_datetime}
        except Exception:
            pass
    try:
        geo = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=timeout).json().get("results", [])
        if not geo:
            raise ValueError("geocoding unavailable")
        lat, lon, tz = geo[0]["latitude"], geo[0]["longitude"], geo[0].get("timezone", "auto")
        day = target.date().isoformat()
        payload = requests.get("https://api.open-meteo.com/v1/forecast", params={"latitude": lat, "longitude": lon, "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m", "start_date": day, "end_date": day, "timezone": tz}, timeout=timeout).json()
        h = payload.get("hourly", {})
        times = h.get("time", [])
        if not times:
            raise ValueError("hourly forecast unavailable")
        idx = min(range(len(times)), key=lambda i: abs(datetime.fromisoformat(times[i]) - target))
        temp = h.get("temperature_2m", [None])[idx]
        humidity = h.get("relative_humidity_2m", [None])[idx]
        rain = h.get("precipitation", [None])[idx]
        wind = h.get("wind_speed_10m", [None])[idx]
        return {"status": "ok", "completeness": "已獲取", "source": "Open-Meteo（免費後備）", "city": city, "temp_c": temp, "humidity": humidity, "wind_kmh": wind, "rain_mm": rain, "label": _label(temp, humidity, rain, wind), "target": match_datetime}
    except Exception as exc:
        return {"status": "unavailable", "completeness": "未獲取", "source": "未取得", "city": city, "error": str(exc), "target": match_datetime}
