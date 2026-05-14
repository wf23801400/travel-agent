"""搜索兴趣点节点。"""

from src.tools import POISearchInput, search_pois

from ..state import TravelAgentState


async def search_poi(state: TravelAgentState) -> dict:
    """调用 poi_search.search_pois 搜索目的地周边兴趣点。"""
    request = state.get("request")
    if request is None:
        return {"poi_data": None}

    # 为每个兴趣类别分别搜索后合并去重，特别搜索住宿
    all_places: dict[str, object] = {}
    for category in ("景点", "美食", "购物", "自然", "住宿"):
        poi_input = POISearchInput(
            destination=request.destination,
            category=category,
            radius_km=10.0,
            limit=5,
        )
        result = await search_pois(poi_input)
        for place in result.places:
            if place.name not in all_places:
                all_places[place.name] = place

    from src.tools import POISearchOutput

    poi_data = POISearchOutput(places=list(all_places.values()))  # type: ignore[arg-type]
    return {"poi_data": poi_data}
