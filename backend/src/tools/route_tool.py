"""路径规划工具 — 通过高德地图 API 查询出发地到目的地的路线方案。"""

import math
import logging

from pydantic import BaseModel, Field

from src.services.amap_client import get_client
from src.tools.geo_tool import get_city_coords

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0


class RouteInput(BaseModel):
    """路径规划输入。"""

    origin: str = Field(..., description="出发城市", examples=["北京"])
    destination: str = Field(..., description="到达城市", examples=["上海"])
    transport_mode: str = Field(default="driving", description="交通方式")


class TransitOption(BaseModel):
    """交通方式选项。"""

    mode: str = Field(..., description="交通方式")
    duration_hours: float = Field(..., description="预估耗时（小时）")
    cost_estimate: float = Field(default=0.0, description="预估花费（元）")
    description: str = Field(default="", description="方案描述")


class RouteOutput(BaseModel):
    """路径规划输出。"""

    origin: str = Field(..., description="出发城市")
    destination: str = Field(..., description="到达城市")
    distance_km: float = Field(..., description="直线距离 (km)")
    driving_distance_km: float = Field(default=0.0, description="驾车距离 (km)")
    driving_duration_hours: float = Field(default=0.0, description="驾车时长 (小时)")
    transit_options: list[TransitOption] = Field(default_factory=list, description="交通方式选项")
    source: str = Field(default="amap", description="数据来源")


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间的直线距离（Haversine 公式）。"""
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


async def get_route(params: RouteInput) -> RouteOutput:
    """规划两个城市间的路线方案。

    优先调用高德地图驾车路径规划 API 获取实时路线数据，
    API 不可用时降级使用 Haversine 距离估算。
    """
    # 获取两个城市的坐标
    origin_coords = await get_city_coords(params.origin)
    dest_coords = await get_city_coords(params.destination)

    if origin_coords is None or dest_coords is None:
        return RouteOutput(
            origin=params.origin,
            destination=params.destination,
            distance_km=0.0,
            source="fallback",
            transit_options=[],
        )

    straight_distance = _haversine(origin_coords.lat, origin_coords.lng, dest_coords.lat, dest_coords.lng)

    # 尝试高德驾车路径规划
    client = get_client()
    driving_dist = 0.0
    driving_dur = 0.0

    if client.is_available:
        try:
            origin_loc = f"{origin_coords.lng},{origin_coords.lat}"
            dest_loc = f"{dest_coords.lng},{dest_coords.lat}"
            result = await client.driving_route(origin_loc, dest_loc)
            if result.get("success") and result.get("routes"):
                route = result["routes"][0]
                driving_dist = route.get("distance_meters", 0) / 1000.0
                driving_dur = route.get("duration_seconds", 0) / 3600.0
        except Exception as e:
            logger.warning("高德路径规划失败，使用距离估算: %s", str(e))

    if driving_dist <= 0:
        # 降级：直线距离 × 1.4 估算实际驾车距离
        driving_dist = round(straight_distance * 1.4, 1)
        driving_dur = round(driving_dist / 60.0, 1)  # 假设平均60km/h

    # 根据距离建议交通方式
    transit_options = _suggest_transit(straight_distance, driving_dist, driving_dur)

    return RouteOutput(
        origin=params.origin,
        destination=params.destination,
        distance_km=round(straight_distance, 1),
        driving_distance_km=round(driving_dist, 1),
        driving_duration_hours=round(driving_dur, 1),
        transit_options=transit_options,
        source="amap" if client.is_available else "fallback",
    )


def _suggest_transit(distance_km: float, driving_dist: float, driving_dur: float) -> list[TransitOption]:
    """根据距离推荐交通方式。"""
    options = []

    # 驾车
    options.append(TransitOption(
        mode="驾车",
        duration_hours=driving_dur,
        cost_estimate=round(driving_dist * 0.6, 0),  # 每公里0.6元估算油费过路费
        description=f"驾车约 {driving_dur:.1f} 小时，全程约 {driving_dist:.0f} 公里",
    ))

    if distance_km >= 500:
        # 飞机
        flight_hours = round(1.5 + distance_km / 800.0, 1)
        options.append(TransitOption(
            mode="飞机",
            duration_hours=flight_hours,
            cost_estimate=round(500 + distance_km * 0.3, 0),
            description=f"飞行约 {flight_hours:.1f} 小时（含机场时间）",
        ))

    if 100 <= distance_km <= 2000:
        # 高铁
        train_hours = round(distance_km / 300.0, 1)
        options.append(TransitOption(
            mode="高铁",
            duration_hours=train_hours,
            cost_estimate=round(distance_km * 0.5, 0),
            description=f"高铁约 {train_hours:.1f} 小时",
        ))

    return options
