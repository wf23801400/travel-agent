"""POI 搜索工具 — 通过高德地图 API 搜索目的地周边的兴趣点，API 不可用时降级使用内置数据。"""

import asyncio
import random
import logging

from pydantic import BaseModel, Field

from src.services.amap_client import get_client, POI_TYPES

logger = logging.getLogger(__name__)

# ===== 兜底 POI 数据池（高德 API 不可用时使用） =====
FALLBACK_POOL: dict[str, list[dict]] = {
    "东京": [
        {"name": "浅草寺", "lat": 35.7148, "lng": 139.7967, "category": "景点", "rating": 4.5, "address": "台东区浅草2-3-1"},
        {"name": "东京塔", "lat": 35.6586, "lng": 139.7454, "category": "景点", "rating": 4.3, "address": "港区芝公园4-2-8"},
        {"name": "筑地市场", "lat": 35.6654, "lng": 139.7707, "category": "美食", "rating": 4.6, "address": "中央区筑地"},
        {"name": "银座商圈", "lat": 35.6717, "lng": 139.7650, "category": "购物", "rating": 4.4, "address": "中央区银座"},
        {"name": "上野公园", "lat": 35.7146, "lng": 139.7732, "category": "自然", "rating": 4.5, "address": "台东区上野公园"},
        {"name": "明治神宫", "lat": 35.6764, "lng": 139.6993, "category": "景点", "rating": 4.7, "address": "涩谷区代代木神园町1-1"},
        {"name": "秋叶原", "lat": 35.7023, "lng": 139.7745, "category": "购物", "rating": 4.4, "address": "千代田区秋叶原"},
        {"name": "涩谷十字路口", "lat": 35.6595, "lng": 139.7004, "category": "景点", "rating": 4.2, "address": "涩谷区涩谷"},
        {"name": "新宿御苑", "lat": 35.6852, "lng": 139.7100, "category": "自然", "rating": 4.5, "address": "新宿区内藤町"},
        {"name": "六本木之丘", "lat": 35.6605, "lng": 139.7292, "category": "购物", "rating": 4.3, "address": "港区六本木6-10-1"},
        {"name": "一兰拉面", "lat": 35.6758, "lng": 139.7184, "category": "美食", "rating": 4.4, "address": "新宿区新宿3-34-11"},
        {"name": "蟹道乐", "lat": 35.6711, "lng": 139.7676, "category": "美食", "rating": 4.5, "address": "中央区银座8-7"},
    ],
    "巴黎": [
        {"name": "埃菲尔铁塔", "lat": 48.8584, "lng": 2.2945, "category": "景点", "rating": 4.7, "address": "Champ de Mars, 5 Avenue Anatole France"},
        {"name": "卢浮宫", "lat": 48.8606, "lng": 2.3376, "category": "景点", "rating": 4.8, "address": "Rue de Rivoli"},
        {"name": "巴黎圣母院", "lat": 48.8530, "lng": 2.3499, "category": "景点", "rating": 4.6, "address": "6 Parvis Notre-Dame"},
        {"name": "香榭丽舍大街", "lat": 48.8698, "lng": 2.3075, "category": "购物", "rating": 4.5, "address": "Avenue des Champs-Élysées"},
        {"name": "蒙马特高地", "lat": 48.8867, "lng": 2.3431, "category": "景点", "rating": 4.4, "address": "Montmartre"},
        {"name": "奥赛博物馆", "lat": 48.8600, "lng": 2.3266, "category": "景点", "rating": 4.7, "address": "1 Rue de la Légion d'Honneur"},
        {"name": "老佛爷百货", "lat": 48.8738, "lng": 2.3322, "category": "购物", "rating": 4.3, "address": "40 Boulevard Haussmann"},
        {"name": "Le Meurice 餐厅", "lat": 48.8652, "lng": 2.3281, "category": "美食", "rating": 4.7, "address": "228 Rue de Rivoli"},
        {"name": "塞纳河游船", "lat": 48.8600, "lng": 2.2930, "category": "景点", "rating": 4.5, "address": "Port de la Bourdonnais"},
    ],
    "北京": [
        {"name": "故宫博物院", "lat": 39.9163, "lng": 116.3972, "category": "景点", "rating": 4.9, "address": "东城区景山前街4号"},
        {"name": "长城（八达岭）", "lat": 40.3542, "lng": 116.0139, "category": "景点", "rating": 4.8, "address": "延庆区G6京藏高速58号出口"},
        {"name": "天坛公园", "lat": 39.8822, "lng": 116.4066, "category": "景点", "rating": 4.6, "address": "东城区天坛内东里7号"},
        {"name": "颐和园", "lat": 39.9998, "lng": 116.2755, "category": "自然", "rating": 4.7, "address": "海淀区新建宫门路19号"},
        {"name": "三里屯太古里", "lat": 39.9337, "lng": 116.4551, "category": "购物", "rating": 4.3, "address": "朝阳区三里屯路19号"},
        {"name": "王府井步行街", "lat": 39.9121, "lng": 116.4111, "category": "购物", "rating": 4.1, "address": "东城区王府井大街"},
        {"name": "全聚德烤鸭（前门店）", "lat": 39.8963, "lng": 116.3918, "category": "美食", "rating": 4.4, "address": "东城区前门大街32号"},
        {"name": "南锣鼓巷", "lat": 39.9375, "lng": 116.4039, "category": "美食", "rating": 4.2, "address": "东城区南锣鼓巷"},
        {"name": "北海公园", "lat": 39.9253, "lng": 116.3894, "category": "自然", "rating": 4.4, "address": "西城区文津街1号"},
    ],
    "上海": [
        {"name": "外滩", "lat": 31.2400, "lng": 121.4900, "category": "景点", "rating": 4.7, "address": "黄浦区中山东一路"},
        {"name": "东方明珠塔", "lat": 31.2397, "lng": 121.4998, "category": "景点", "rating": 4.5, "address": "浦东新区世纪大道1号"},
        {"name": "迪士尼乐园", "lat": 31.1430, "lng": 121.6580, "category": "景点", "rating": 4.8, "address": "浦东新区川沙镇黄赵路310号"},
        {"name": "南京路步行街", "lat": 31.2388, "lng": 121.4717, "category": "购物", "rating": 4.3, "address": "黄浦区南京东路"},
        {"name": "豫园", "lat": 31.2272, "lng": 121.4952, "category": "景点", "rating": 4.4, "address": "黄浦区豫园老街279号"},
        {"name": "新天地", "lat": 31.2184, "lng": 121.4741, "category": "购物", "rating": 4.2, "address": "黄浦区太仓路181弄"},
        {"name": "南翔馒头店（豫园店）", "lat": 31.2268, "lng": 121.4952, "category": "美食", "rating": 4.3, "address": "黄浦区豫园路87号"},
        {"name": "鼎泰丰（新天地店）", "lat": 31.2186, "lng": 121.4745, "category": "美食", "rating": 4.5, "address": "黄浦区兴业路123弄"},
    ],
}

# 兴趣类别 → 高德POI类型码 映射
INTEREST_TO_AMAP_TYPE = {
    "景点": "060000",
    "风景名胜": "060000",
    "历史": "060000",
    "博物馆": "060000",
    "美食": "050000",
    "餐饮": "050000",
    "购物": "060100",
    "自然": "060000",
    "公园": "060000",
    "户外": "080000",
    "住宿": "100000",
    "酒店": "100000",
    "艺术": "060000",
    "文化": "060000",
}


class POISearchInput(BaseModel):
    """POI 搜索输入。"""

    destination: str = Field(..., description="目的地城市", examples=["东京"])
    category: str = Field(default="", description="兴趣点类别筛选（景点/美食/购物/自然等）")
    radius_km: float = Field(default=5.0, ge=0.1, le=50.0, description="搜索半径 (km)")
    limit: int = Field(default=10, ge=1, le=50, description="返回结果数量上限")
    interests: list[str] = Field(default_factory=list, description="兴趣标签列表")


class Place(BaseModel):
    """兴趣点信息。"""

    name: str = Field(..., description="地点名称")
    address: str = Field(default="", description="地址")
    lat: float = Field(..., ge=-90, le=90, description="纬度")
    lng: float = Field(..., ge=-180, le=180, description="经度")
    rating: float = Field(default=0.0, ge=0, le=5, description="评分")
    category: str = Field(default="", description="分类")
    description: str = Field(default="", description="简要描述")


class POISearchOutput(BaseModel):
    """POI 搜索结果。"""

    places: list[Place] = Field(default_factory=list, description="兴趣点列表")
    source: str = Field(default="amap", description="数据来源: amap 或 fallback")


async def _search_amap(destination: str, category: str, interests: list[str], limit: int) -> list[dict] | None:
    """通过高德 API 搜索 POI。

    支持任意地点：如果 destination 是已知城市则按城市搜索，
    否则先地理编码获取坐标，再按坐标周边搜索。
    """
    client = get_client()
    if not client.is_available:
        return None

    # 确定要搜索的 POI 类型
    type_names = []
    if category:
        type_names.append(category)
    else:
        type_names = ["景点", "美食"]
        if interests:
            type_names = [i for i in interests if i in INTEREST_TO_AMAP_TYPE]

    # 判断 destination 是否为已知城市
    is_city = destination in FALLBACK_POOL or destination in (
        "北京", "上海", "广州", "深圳", "成都", "杭州", "武汉", "西安",
        "南京", "重庆", "厦门", "青岛", "大连", "三亚", "昆明", "哈尔滨",
        "长沙", "苏州", "拉萨", "乌鲁木齐", "东京", "大阪", "京都", "首尔",
        "曼谷", "巴黎", "伦敦", "纽约", "洛杉矶", "悉尼", "新加坡", "迪拜",
        "香港", "台北", "横滨",
    )

    all_pois = []
    if is_city:
        # 城市模式：按城市名搜索
        for type_name in type_names[:3]:
            result = await client.poi_search_by_type(city=destination, type_name=type_name, page=1, offset=limit)
            if result.get("success"):
                for p in result.get("pois", []):
                    all_pois.append({
                        "name": p.get("name", ""),
                        "address": p.get("address", ""),
                        "lat": p.get("lat", 0.0),
                        "lng": p.get("lng", 0.0),
                        "rating": float(p.get("biz_ext_rating", 3.0) or 3.0),
                        "category": type_name,
                        "description": "",
                    })

            # 如果城市搜索返回 0 条，降级为周边搜索（尤其对海外城市/住宿有效）
            if not result.get("pois"):
                geo_fallback = await client.geocode(destination)
                if geo_fallback.get("success") and geo_fallback.get("geocodes"):
                    center = geo_fallback["geocodes"][0]
                    around = await client.poi_search_around(
                        lat=center["lat"], lng=center["lng"],
                        type_name=type_name,
                        radius_meters=10000,
                        offset=limit,
                    )
                    if around.get("success"):
                        for p in around.get("pois", []):
                            all_pois.append({
                                "name": p.get("name", ""),
                                "address": p.get("address", ""),
                                "lat": p.get("lat", 0.0),
                                "lng": p.get("lng", 0.0),
                                "rating": float(p.get("biz_ext_rating", 3.0) or 3.0),
                                "category": type_name,
                                "description": "",
                            })
    else:
        # 非城市模式：先地理编码获取坐标，再按坐标周边搜索
        try:
            geo_result = await client.geocode(destination)
            if not geo_result.get("success") or not geo_result.get("geocodes"):
                return None
            center = geo_result["geocodes"][0]
            lat, lng = center["lat"], center["lng"]

            for type_name in type_names[:3]:
                result = await client.poi_search_around(
                    lat=lat, lng=lng,
                    type_name=type_name,
                    radius_meters=3000,
                    offset=limit,
                )
                if result.get("success"):
                    for p in result.get("pois", []):
                        all_pois.append({
                            "name": p.get("name", ""),
                            "address": p.get("address", ""),
                            "lat": p.get("lat", 0.0),
                            "lng": p.get("lng", 0.0),
                            "rating": float(p.get("biz_ext_rating", 3.0) or 3.0),
                            "category": type_name,
                            "description": "",
                        })
        except Exception:
            return None

    if all_pois:
        seen = set()
        unique = []
        for p in all_pois:
            key = (p["name"], round(p["lat"], 4), round(p["lng"], 4))
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique[:limit]

    return None


async def search_pois(params: POISearchInput) -> POISearchOutput:
    """搜索目的地周边的兴趣点。

    优先调用高德地图 API 获取实时 POI 数据。
    如果高德 API 不可用或未返回结果，降级使用内置兜底数据。
    """
    # 尝试高德 API
    try:
        amap_result = await _search_amap(params.destination, params.category, params.interests, params.limit)
        if amap_result:
            places = [
                Place(
                    name=p["name"],
                    address=p.get("address", f"{params.destination}{p['name']}附近"),
                    lat=p["lat"],
                    lng=p["lng"],
                    rating=p.get("rating", 3.0),
                    category=p.get("category", params.category or "景点"),
                    description=p.get("description", f"{p['name']}是{params.destination}的热门去处。"),
                )
                for p in amap_result
            ]
            return POISearchOutput(places=places, source="amap")
    except Exception as e:
        logger.warning("高德API POI搜索失败，降级使用兜底数据: %s", str(e))

    # 降级：使用内置数据
    pool = FALLBACK_POOL.get(params.destination, [])
    if not pool:
        # 无兜底数据时返回空
        return POISearchOutput(places=[], source="fallback")

    filtered = pool
    if params.category:
        filtered = [p for p in filtered if p["category"] == params.category]

    selected = random.sample(filtered, min(len(filtered), params.limit)) if filtered else []
    places = [
        Place(
            name=p["name"],
            address=p.get("address", f"{params.destination}{p['name']}附近"),
            lat=p["lat"],
            lng=p["lng"],
            rating=p.get("rating", 4.0),
            category=p["category"],
            description=f"{p['name']}是{params.destination}的热门{'景点' if p['category'] == '景点' else '去处'}。",
        )
        for p in selected
    ]
    return POISearchOutput(places=places, source="fallback")
