"""组装上下文节点 — 将所有工具返回数据拼接为 context dict，供 LLM 使用。"""

import datetime
import json


from ..state import TravelAgentState


async def assemble_context(state: TravelAgentState) -> dict:
    """将天气、POI、预算数据组装为 LLM 可读的上下文。"""
    request = state.get("request")
    weather_data = state.get("weather_data")
    poi_data = state.get("poi_data")
    budget_data = state.get("budget_data")

    context: dict = {}

    if request is not None:
        context["origin"] = request.origin
        context["destination"] = request.destination
        context["start_date"] = request.start_date.isoformat()
        context["end_date"] = request.end_date.isoformat()
        context["travelers"] = request.travelers
        context["budget_amount"] = request.budget_amount
        context["pace"] = request.pace
        context["interests"] = request.interests
        context["dietary_restrictions"] = request.dietary_restrictions

    if weather_data is not None:
        context["weather"] = [
            {
                "date": w.date.isoformat(),
                "temp_high": w.temp_high,
                "temp_low": w.temp_low,
                "condition": w.condition,
                "humidity": w.humidity,
                "precipitation_chance": w.precipitation_chance,
            }
            for w in weather_data.forecast
        ]

    if poi_data is not None:
        all_pois = [
            {
                "name": p.name,
                "category": p.category,
                "rating": p.rating,
                "address": p.address,
                "lat": p.lat,
                "lng": p.lng,
                "description": p.description,
            }
            for p in poi_data.places
        ]
        context["pois"] = all_pois

        # 分离住宿数据，供 LLM 住宿推荐专用
        hotels = [p for p in all_pois if p["category"] == "住宿"]
        context["hotels"] = hotels[:5]  # 最多推荐5家

    if budget_data is not None:
        context["budget"] = {
            "breakdown": {
                "accommodation": budget_data.breakdown.accommodation,
                "food": budget_data.breakdown.food,
                "transport": budget_data.breakdown.transport,
                "attractions": budget_data.breakdown.attractions,
                "shopping": budget_data.breakdown.shopping,
                "misc": budget_data.breakdown.misc,
                "total": budget_data.breakdown.total,
            },
            "currency": budget_data.currency,
            "per_person": budget_data.per_person,
        }

    # 注入知识库检索结果（攻略片段）
    knowledge_results = state.get("knowledge_results", [])
    if knowledge_results:
        context["knowledge"] = [
            {
                "title": r["title"],
                "text": r["text"],
                "score": r["score"],
            }
            for r in knowledge_results
        ]

    # 生成 LLM system prompt 所需的文本摘要
    context["summary"] = _build_summary(context)

    return {"context": context}


def _build_summary(context: dict) -> str:
    """根据上下文生成供 LLM 使用的文本摘要。"""
    parts: list[str] = []
    parts.append(f"目的地: {context.get('destination', '未知')}")
    parts.append(f"旅行日期: {context.get('start_date', '?')} 至 {context.get('end_date', '?')}")
    parts.append(f"人数: {context.get('travelers', 1)}")
    budget_amount = context.get('budget_amount')
    if budget_amount and budget_amount > 0:
        parts.append(f"预算: {budget_amount:.0f} 元")
    else:
        parts.append(f"预算: 自动估算")
    parts.append(f"节奏: {context.get('pace', 'moderate')}")
    parts.append(f"兴趣: {', '.join(context.get('interests', [])) or '无'}")

    weather = context.get("weather", [])
    if weather:
        parts.append(f"天气概况: {json.dumps(weather, ensure_ascii=False)}")

    pois = context.get("pois", [])
    if pois:
        poi_names = [p["name"] for p in pois]
        parts.append(f"推荐地点: {', '.join(poi_names)}")

    budget = context.get("budget", {})
    if budget:
        parts.append(
            f"预估总费用: {budget.get('per_person', 0):.0f}/人 "
            f"({budget.get('currency', 'CNY')})"
        )

    hotels = context.get("hotels", [])
    if hotels:
        hotel_names = [h["name"] for h in hotels]
        parts.append(f"推荐住宿: {', '.join(hotel_names)}")

    knowledge = context.get("knowledge", [])
    if knowledge:
        k_titles = [k["title"] for k in knowledge]
        parts.append(f"攻略参考: {', '.join(k_titles)}")

    return "\n".join(parts)
