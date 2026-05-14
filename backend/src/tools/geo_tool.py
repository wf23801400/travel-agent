"""地理编码工具 — 通过高德地图 API 进行地理编码/逆地理编码和距离计算。"""

import math
import logging

from pydantic import BaseModel, Field

from src.services.amap_client import get_client

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0

# 兜底城市坐标（高德 API 不可用时使用）
FALLBACK_COORDS: dict[str, tuple[float, float]] = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "成都": (30.5728, 104.0668),
    "杭州": (30.2741, 120.1551),
    "武汉": (30.5928, 114.3055),
    "西安": (34.3416, 108.9398),
    "南京": (32.0603, 118.7969),
    "重庆": (29.4316, 106.9123),
    "厦门": (24.4798, 118.0894),
    "青岛": (36.0671, 120.3826),
    "大连": (38.9140, 121.6147),
    "三亚": (18.2528, 109.5120),
    "昆明": (25.0389, 102.7183),
    "哈尔滨": (45.8038, 126.5350),
    "长沙": (28.2282, 112.9388),
    "苏州": (31.2990, 120.5853),
    "拉萨": (29.6500, 91.1000),
    "乌鲁木齐": (43.8256, 87.6168),
    # 国外城市
    "东京": (35.6762, 139.6503),
    "横滨": (35.4437, 139.6380),
    "大阪": (34.6937, 135.5023),
    "京都": (35.0116, 135.7681),
    "首尔": (37.5665, 126.9780),
    "曼谷": (13.7563, 100.5018),
    "巴黎": (48.8566, 2.3522),
    "伦敦": (51.5074, -0.1278),
    "纽约": (40.7128, -74.0060),
    "洛杉矶": (34.0522, -118.2437),
    "悉尼": (-33.8688, 151.2093),
    "新加坡": (1.3521, 103.8198),
    "迪拜": (25.2048, 55.2708),
    "香港": (22.3193, 114.1694),
    "台北": (25.0330, 121.5654),
}


class GeoCoord(BaseModel):
    """地理坐标。"""

    lat: float = Field(..., ge=-90, le=90, description="纬度")
    lng: float = Field(..., ge=-180, le=180, description="经度")


class GeoCoordInput(BaseModel):
    """地理编码输入。"""

    address: str = Field(..., description="地址或城市名称")
    city: str = Field(default="", description="限定城市，可选")


class GeoCoordOutput(BaseModel):
    """地理编码输出。"""

    coords: list[GeoCoord] = Field(default_factory=list, description="坐标列表")
    formatted_addresses: list[str] = Field(default_factory=list, description="格式化地址列表")


class DistCalcInput(BaseModel):
    """城市距离计算输入。"""

    city_a: str = Field(..., description="城市A名称")
    city_b: str = Field(..., description="城市B名称")


class DistCalcOutput(BaseModel):
    """城市距离计算输出。"""

    city_a: str = Field(..., description="城市A")
    city_b: str = Field(..., description="城市B")
    distance_km: float = Field(..., ge=0, description="直线距离 (km)")


# 保留旧模型以兼容现有调用方
class GeoInput(BaseModel):
    """距离计算输入（坐标版）— 保持向后兼容。"""

    lat1: float = Field(..., ge=-90, le=90, description="起点纬度")
    lng1: float = Field(..., ge=-180, le=180, description="起点经度")
    lat2: float = Field(..., ge=-90, le=90, description="终点纬度")
    lng2: float = Field(..., ge=-180, le=180, description="终点经度")
    origin: str = Field(default="起点", description="起点名称")
    destination: str = Field(default="终点", description="终点名称")


class GeoOutput(BaseModel):
    """距离计算结果 — 保持向后兼容。"""

    distance_km: float = Field(..., ge=0, description="距离 (km)")
    distance_miles: float = Field(..., ge=0, description="距离 (mi)")
    origin: str = Field(..., description="起点名称")
    destination: str = Field(..., description="终点名称")


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine 公式计算两点间球面距离 (km)。"""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def get_city_coords(city_name: str) -> GeoCoord | None:
    """通过高德地图地理编码 API 获取城市坐标，API 不可用时降级使用兜底数据。

    Args:
        city_name: 城市名称，如 "北京"、"上海"

    Returns:
        GeoCoord | None: 城市经纬度，失败时返回 None
    """
    client = get_client()
    if client.is_available:
        result = await client.geocode(city_name)
        if result.get("success") and result.get("geocodes"):
            first = result["geocodes"][0]
            return GeoCoord(lat=first["lat"], lng=first["lng"])

    # 降级：使用兜底坐标
    coords = FALLBACK_COORDS.get(city_name)
    if coords:
        logger.debug("使用兜底坐标: %s -> (%s, %s)", city_name, coords[0], coords[1])
        return GeoCoord(lat=coords[0], lng=coords[1])

    logger.warning("未找到城市坐标: %s", city_name)
    return None


async def get_location(address: str, city: str = "") -> GeoCoord | None:
    """通过高德地图地理编码 API 将地址转为坐标。

    Args:
        address: 详细地址，如 "北京市朝阳区阜通东大街6号"
        city: 限定城市，可选

    Returns:
        GeoCoord | None: 地址经纬度，失败时返回 None
    """
    client = get_client()
    result = await client.geocode(address, city)
    if not result.get("success") or not result.get("geocodes"):
        return None
    first = result["geocodes"][0]
    return GeoCoord(lat=first["lat"], lng=first["lng"])


async def get_address(lat: float, lng: float) -> str:
    """通过高德地图逆地理编码 API 将坐标转为地址。

    Args:
        lat: 纬度
        lng: 经度

    Returns:
        str: 格式化地址，失败时返回空字符串
    """
    client = get_client()
    result = await client.re_geocode(lng, lat)
    if not result.get("success"):
        return ""
    return result.get("formatted_address", "")


async def get_city_distance(city_a: str, city_b: str) -> float | None:
    """计算两个城市之间的直线距离。

    先通过 geocode 获取两城市坐标，再用 Haversine 公式计算。

    Args:
        city_a: 城市A名称
        city_b: 城市B名称

    Returns:
        float | None: 距离 (km)，失败时返回 None
    """
    coord_a = await get_city_coords(city_a)
    coord_b = await get_city_coords(city_b)
    if coord_a is None or coord_b is None:
        return None
    return round(_haversine(coord_a.lat, coord_a.lng, coord_b.lat, coord_b.lng), 2)


async def calculate_distance(params: DistCalcInput) -> DistCalcOutput:
    """计算两个城市之间的直线距离（结构化输入输出）。

    Args:
        params: DistCalcInput — city_a, city_b

    Returns:
        DistCalcOutput: 包含距离和城市名称
    """
    try:
        km = await get_city_distance(params.city_a, params.city_b)
        if km is None:
            return DistCalcOutput(city_a=params.city_a, city_b=params.city_b, distance_km=0.0)
        return DistCalcOutput(city_a=params.city_a, city_b=params.city_b, distance_km=km)
    except Exception:
        return DistCalcOutput(city_a=params.city_a, city_b=params.city_b, distance_km=0.0)


# 保留旧的坐标版距离计算以兼容现有调用方
async def calculate_coord_distance(params: GeoInput) -> GeoOutput:
    """计算两个地理坐标之间的真实球面距离（Haversine 公式）。

    保留此函数以兼容旧的调用方。
    """
    try:
        km = round(_haversine(params.lat1, params.lng1, params.lat2, params.lng2), 2)
        miles = round(km * 0.621371, 2)
        return GeoOutput(
            distance_km=km,
            distance_miles=miles,
            origin=params.origin,
            destination=params.destination,
        )
    except Exception:
        return GeoOutput(
            distance_km=0.0,
            distance_miles=0.0,
            origin=params.origin,
            destination=params.destination,
        )
