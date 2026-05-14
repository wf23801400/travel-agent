"""高德地图 Web API HTTP 客户端 — 统一封装 API key、限流、重试、错误处理。"""

import asyncio
import logging
from typing import Optional

import httpx

from src.models.settings import Settings

logger = logging.getLogger(__name__)

AMAP_BASE = "https://restapi.amap.com/v3"

POI_TYPES: dict[str, str] = {
    "景点": "060000",
    "风景名胜": "060000",
    "餐饮": "050000",
    "美食": "050000",
    "购物": "060100",
    "住宿": "100000",
    "酒店": "100000",
    "交通设施": "150000",
}

_client: Optional["AmapClient"] = None


def get_client() -> "AmapClient":
    """获取 AmapClient 单例。"""
    global _client
    if _client is None:
        _client = AmapClient(Settings())
    return _client


def reset_client() -> None:
    """重置客户端单例（主要用于测试）。"""
    global _client
    _client = None


class AmapClient:
    """高德地图 Web API HTTP 客户端。

    封装 API key 注入、超时、重试和结构化错误返回。
    """

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.amap_api_key
        self._base_url = settings.amap_api_base
        self._timeout = 10.0
        self._max_retries = 3

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    async def _get(self, path: str, params: dict) -> dict:
        """发送 GET 请求，带重试和指数退避。"""
        if not self._api_key:
            return {"success": False, "error": "高德地图 API key 未配置"}

        params["key"] = self._api_key

        last_error = ""
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.get(f"{self._base_url}{path}", params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    if int(data.get("status", "0")) == 1:
                        return data
                    last_error = data.get("info", "未知错误")
                    logger.warning("高德 API 返回错误: %s (path=%s)", last_error, path)
                    return {"success": False, "error": last_error}
            except httpx.TimeoutException:
                last_error = f"请求超时 (第{attempt + 1}次)"
                logger.warning("高德 API 超时: %s (path=%s)", last_error, path)
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                logger.warning("高德 API HTTP 错误: %s (path=%s)", last_error, path)
            except Exception as e:
                last_error = str(e)
                logger.warning("高德 API 请求异常: %s (path=%s)", last_error, path)

            if attempt < self._max_retries - 1:
                wait = 2**attempt  # 1s, 2s, 4s
                await asyncio.sleep(wait)

        return {"success": False, "error": last_error}

    async def geocode(self, address: str, city: str = "") -> dict:
        """地理编码 — 地址转经纬度。

        Args:
            address: 结构化地址信息，如 "北京市朝阳区阜通东大街6号"
            city: 指定查询的城市，可选

        Returns:
            dict: 成功时含 geocodes 列表，每项有 location(lng,lat)、formatted_address 等
        """
        params = {"address": address}
        if city:
            params["city"] = city
        result = await self._get("/geocode/geo", params)
        if result.get("success") is False:
            return result
        geocodes = result.get("geocodes", [])
        parsed = []
        for g in geocodes:
            loc = g.get("location", "0,0")
            parts = loc.split(",")
            parsed.append({
                "formatted_address": g.get("formatted_address", address),
                "lng": float(parts[0]) if len(parts) >= 2 else 0.0,
                "lat": float(parts[1]) if len(parts) >= 2 else 0.0,
                "adcode": g.get("adcode", ""),
                "level": g.get("level", ""),
            })
        return {"success": True, "geocodes": parsed, "count": int(result.get("count", "0"))}

    async def re_geocode(self, lng: float, lat: float) -> dict:
        """逆地理编码 — 经纬度转地址。

        Args:
            lng: 经度
            lat: 纬度

        Returns:
            dict: 成功时含 formatted_address、addressComponent(省/市/区) 等
        """
        result = await self._get("/geocode/regeo", {
            "location": f"{lng},{lat}",
        })
        if result.get("success") is False:
            return result
        regeo = result.get("regeocode", {})
        addr = regeo.get("addressComponent", {})
        return {
            "success": True,
            "formatted_address": regeo.get("formatted_address", ""),
            "province": addr.get("province", ""),
            "city": addr.get("city", []) if isinstance(addr.get("city"), list) else addr.get("city", ""),
            "district": addr.get("district", ""),
            "adcode": addr.get("adcode", ""),
            "pois": regeo.get("pois", []),
        }

    async def poi_search(
        self,
        keywords: str,
        city: str = "",
        types: str = "",
        page: int = 1,
        offset: int = 20,
    ) -> dict:
        """POI 搜索 — 搜索兴趣点。

        Args:
            keywords: 查询关键词
            city: 查询城市
            types: POI 类型代码，如 "060000"(风景名胜)、"050000"(餐饮) 等
            page: 页码，从1开始
            offset: 每页条数，最大25

        Returns:
            dict: 成功时含 pois 列表，每项有 name、location(lng,lat)、address、type 等
        """
        params = {
            "keywords": keywords,
            "city": city,
            "offset": min(offset, 25),
            "page": page,
        }
        if types:
            params["types"] = types
        result = await self._get("/place/text", params)
        if result.get("success") is False:
            return result
        pois_raw = result.get("pois", [])
        pois = []
        for p in pois_raw:
            loc = p.get("location", "0,0")
            parts = loc.split(",")
            pois.append({
                "name": p.get("name", ""),
                "lng": float(parts[0]) if len(parts) >= 2 else 0.0,
                "lat": float(parts[1]) if len(parts) >= 2 else 0.0,
                "address": p.get("address", ""),
                "adname": p.get("adname", ""),
                "type": p.get("type", ""),
                "typecode": p.get("typecode", ""),
                "biz_ext_cost": p.get("biz_ext", {}).get("cost", "") if isinstance(p.get("biz_ext"), dict) else "",
                "biz_ext_rating": p.get("biz_ext", {}).get("rating", "") if isinstance(p.get("biz_ext"), dict) else "",
                "photos": [ph.get("url", "") for ph in p.get("photos", [])] if isinstance(p.get("photos"), list) else [],
            })
        return {
            "success": True,
            "pois": pois,
            "count": int(result.get("count", "0")),
            "total_page": int(p.get("pagenum", 1)) if pois else 1 if pois_raw else 1,
        }

    async def weather_forecast(self, city: str) -> dict:
        """天气预报 — 未来4天预报。

        Args:
            city: 城市名称或 adcode

        Returns:
            dict: 成功时含 forecasts 列表，每项有 date、day/night weather、temperature 等
        """
        result = await self._get("/weather/weatherInfo", {
            "city": city,
            "extensions": "all",
        })
        if result.get("success") is False:
            return result
        forecasts = result.get("forecasts", [])
        parsed = []
        for f in forecasts:
            casts = []
            for c in f.get("casts", []):
                casts.append({
                    "date": c.get("date", ""),
                    "day_weather": c.get("dayweather", ""),
                    "night_weather": c.get("nightweather", ""),
                    "day_temp": float(c.get("daytemp", 0)),
                    "night_temp": float(c.get("nighttemp", 0)),
                    "day_wind": c.get("daywind", ""),
                    "night_wind": c.get("nightwind", ""),
                    "day_power": c.get("daypower", ""),
                    "night_power": c.get("nightpower", ""),
                })
            parsed.append({
                "city": f.get("city", city),
                "adcode": f.get("adcode", ""),
                "casts": casts,
            })
        return {"success": True, "forecasts": parsed}

    async def weather_live(self, city: str) -> dict:
        """实时天气 — 当前天气状况。

        Args:
            city: 城市名称或 adcode

        Returns:
            dict: 成功时含 temperature、weather、humidity、winddirection、windpower 等
        """
        result = await self._get("/weather/weatherInfo", {
            "city": city,
            "extensions": "base",
        })
        if result.get("success") is False:
            return result
        lives = result.get("lives", [])
        parsed = []
        for l in lives:
            parsed.append({
                "province": l.get("province", ""),
                "city": l.get("city", city),
                "adcode": l.get("adcode", ""),
                "temperature": float(l.get("temperature", 0)),
                "weather": l.get("weather", ""),
                "humidity": float(l.get("humidity", 0)),
                "winddirection": l.get("winddirection", ""),
                "windpower": str(l.get("windpower", "")),
                "report_time": l.get("reporttime", ""),
            })
        return {"success": True, "lives": parsed}

    async def driving_route(self, origin: str, destination: str) -> dict:
        """驾车路径规划。

        Args:
            origin: 起点坐标，格式 "lng,lat"
            destination: 终点坐标，格式 "lng,lat"

        Returns:
            dict: 成功时含 distance(米)、duration(秒)、tolls、steps 等
        """
        result = await self._get("/direction/driving", {
            "origin": origin,
            "destination": destination,
        })
        if result.get("success") is False:
            return result
        route_raw = result.get("route", {})
        paths = route_raw.get("paths", [])
        parsed = []
        for p in paths:
            parsed.append({
                "distance_meters": int(p.get("distance", 0)),
                "duration_seconds": int(p.get("duration", 0)),
                "toll_distance_meters": int(p.get("toll_distance", 0)),
                "tolls": float(p.get("tolls", 0)),
                "steps": [
                    {
                        "instruction": s.get("instruction", ""),
                        "road": s.get("road", ""),
                        "distance_meters": int(s.get("distance", 0)),
                        "duration_seconds": int(s.get("duration", 0)),
                    }
                    for s in p.get("steps", [])
                ],
            })
        return {"success": True, "routes": parsed}

    async def poi_search_around(
        self,
        lat: float,
        lng: float,
        type_name: str = "",
        radius_meters: int = 5000,
        keywords: str = "",
        page: int = 1,
        offset: int = 25,
    ) -> dict:
        """周边 POI 搜索 — 以指定坐标为中心搜索周边兴趣点。

        Args:
            lat: 中心纬度
            lng: 中心经度
            type_name: 中文类型名，如 "景点"、"餐饮"、"购物"
            radius_meters: 搜索半径（米），默认 5000
            keywords: 附加关键词
            page: 页码
            offset: 每页条数

        Returns:
            dict: 同 poi_search 返回结构
        """
        params: dict = {
            "location": f"{lng},{lat}",
            "radius": max(100, min(radius_meters, 50000)),
            "offset": min(offset, 25),
            "page": page,
        }
        if type_name:
            types = POI_TYPES.get(type_name, "")
            if types:
                params["types"] = types
        if keywords:
            params["keywords"] = keywords

        result = await self._get("/place/around", params)
        if result.get("success") is False:
            return result
        pois_raw = result.get("pois", [])
        pois = []
        for p in pois_raw:
            loc = p.get("location", "0,0")
            parts = loc.split(",")
            pois.append({
                "name": p.get("name", ""),
                "lng": float(parts[0]) if len(parts) >= 2 else 0.0,
                "lat": float(parts[1]) if len(parts) >= 2 else 0.0,
                "address": p.get("address", ""),
                "adname": p.get("adname", ""),
                "type": p.get("type", ""),
                "typecode": p.get("typecode", ""),
                "biz_ext_cost": p.get("biz_ext", {}).get("cost", "") if isinstance(p.get("biz_ext"), dict) else "",
                "biz_ext_rating": p.get("biz_ext", {}).get("rating", "") if isinstance(p.get("biz_ext"), dict) else "",
                "photos": [ph.get("url", "") for ph in p.get("photos", [])] if isinstance(p.get("photos"), list) else [],
                "distance": int(p.get("distance", 0)),
            })
        return {
            "success": True,
            "pois": pois,
            "count": int(result.get("count", "0")),
        }

    async def poi_search_by_type(
        self,
        city: str,
        type_name: str,
        keywords: str = "",
        page: int = 1,
        offset: int = 20,
    ) -> dict:
        """按中文类型名搜索 POI。

        Args:
            city: 城市名称
            type_name: 中文类型名，如 "景点"、"餐饮"、"购物"、"住宿"
            keywords: 附加关键词
            page: 页码
            offset: 每页条数

        Returns:
            dict: 同 poi_search 返回结构
        """
        types = POI_TYPES.get(type_name, "")
        kw = keywords or type_name
        return await self.poi_search(keywords=kw, city=city, types=types, page=page, offset=offset)
