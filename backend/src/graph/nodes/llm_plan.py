"""LLM 行程生成节点 — 调用 LLM（DeepSeek/Claude）基于真实上下文数据生成行程。"""

import datetime
import json
import logging
from typing import Any

from src.models import DayPlan, Itinerary, Location, TimeSlot
from src.services.llm_client import get_llm_client

from ..state import TravelAgentState

logger = logging.getLogger(__name__)


async def llm_plan(state: TravelAgentState) -> dict:
    """调用 LLM 基于天气、POI、预算等真实数据生成完整行程。

    优先调用 DeepSeek/Claude API 生成行程，
    API 不可用时降级使用基于上下文数据的 mock 行程。
    """
    request = state.get("request")
    if request is None:
        return {"itinerary": None}

    context = state.get("context") or {}
    refine_feedback = state.get("refine_feedback")
    retry_count = state.get("retry_count", 0)
    validation_errors = state.get("validation_errors", [])

    # 尝试通过 LLM 生成
    client = get_llm_client()
    if client.is_available:
        try:
            itinerary = await _generate_with_llm(
                client=client,
                request=request,
                context=context,
                refine_feedback=refine_feedback,
                retry_count=retry_count,
                validation_errors=validation_errors,
            )
            if itinerary is not None:
                return {"itinerary": itinerary}
        except Exception as e:
            logger.warning("LLM 行程生成失败，降级使用基于上下文的 mock: %s", str(e))

    # 降级：基于真实上下文数据生成
    itinerary = _generate_fallback(request, context, refine_feedback)
    return {"itinerary": itinerary}


async def _generate_with_llm(
    client: Any,
    request: Any,
    context: dict,
    refine_feedback: str | None,
    retry_count: int,
    validation_errors: list[str],
) -> Itinerary | None:
    """通过 LLM 生成行程。"""
    system_msg = _build_system_prompt()
    user_msg = _build_user_prompt(request, context, refine_feedback, validation_errors)

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    result = await client.chat(
        messages=messages,
        response_model=Itinerary,
        temperature=0.7,
        max_tokens=4096,
    )

    if isinstance(result, Itinerary):
        _recalculate_budget(result, request.travelers)
        return result
    return None


def _recalculate_budget(itinerary: Any, travelers: int) -> None:
    """遍历所有 TimeSlot，重新计算总预算，覆盖 LLM 生成的不稳定值。"""
    total = sum(
        slot.cost
        for day in itinerary.days
        for slot in day.time_slots
    ) * travelers
    itinerary.total_budget_estimate = total


def _build_system_prompt() -> str:
    """构建 LLM system prompt。"""
    return """你是一位专业的旅行规划师，精通全球旅游目的地。
你的任务是根据用户提供的旅行偏好、目的地天气、POI 数据和预算信息，
生成一份详细、合理、个性化的每日行程计划。

## 核心原则
1. 行程必须**切实可行** — 考虑各景点之间的地理距离，不要安排空间上相距太远的活动
2. **节奏合理** — 根据用户选择的节奏（宽松/适中/紧凑）安排活动密度
3. **预算敏感** — 根据用户输入的预算总额合理安排活动开销，控制在预算范围内。住宿费用不应超过总预算的 40%
4. **住宿推荐** — 优先使用 context 中提供的推荐酒店数据，给出具体酒店名称和价格。每个行程日要包含住宿（accommodation）活动
5. **多样化** — 每天的活动类型应多样化，不要全是景点或全是美食
6. **时间合理** — 每个活动的时间段要合理（景点2-3小时，餐饮1-2小时，购物1-2小时）
7. **货币单位** — 所有价格以人民币(元)为单位，不要使用当地货币
8. **攻略优先** — 如果 context 中包含「知识库攻略」片段，优先参考其中的行程安排、费用预算、住宿推荐等实用信息

## 输出格式
严格按照 Itinerary schema 输出，每个 DayPlan 需包含：
- date: 日期
- time_slots: 多个时间段活动
  - start_time/end_time: 时间范围
  - activity_name: 活动名称（中文，具体生动）
  - activity_type: transport/accommodation/food/attraction/shopping/rest/other
  - location: 地点信息（name, lat, lng, address, rating）
  - cost: 预估花费（元）
  - notes: 实用备注（营业时间、预订建议、穿搭建议等）

## 创意与真实性
- 活动名称要具体，如"参观故宫博物院"而不是"游览景点"
- 尽量使用 context 中提供的 POI 数据，确保地点真实存在
- 如果 POI 数据不充分，可以根据城市常识补充合理的地点
- 备注要实用：是否需要预约、预计排队时间、最佳游览时段等"""


def _build_user_prompt(
    request: Any,
    context: dict,
    refine_feedback: str | None,
    validation_errors: list[str],
) -> str:
    """构建用户消息 prompt。"""
    parts = [f"## 旅行需求"]

    if request.origin:
        parts.append(f"- 出发地: {request.origin}")
    parts.append(f"- 目的地: {request.destination}")
    parts.append(f"- 日期: {request.start_date} 至 {request.end_date}")
    parts.append(f"- 人数: {request.travelers}")
    if request.budget_amount and request.budget_amount > 0:
        parts.append(f"- 预算总额: {request.budget_amount:.0f} 元")
    else:
        parts.append(f"- 预算: 自动估算（适中档）")
    parts.append(f"- 行程节奏: {request.pace}")
    if request.interests:
        parts.append(f"- 兴趣偏好: {', '.join(request.interests)}")

    # 天气信息
    weather = context.get("weather", [])
    if weather:
        parts.append(f"\n## 天气预报")
        for w in weather:
            parts.append(
                f"- {w.get('date', '?')}: {w.get('condition', '')}, "
                f"高温{w.get('temp_high', '?')}℃/低温{w.get('temp_low', '?')}℃"
            )

    # POI 数据
    pois = context.get("pois", [])
    if pois:
        parts.append(f"\n## 推荐地点")
        for p in pois:
            rating_str = f"({'★' * int(p.get('rating', 0))})" if p.get('rating') else ""
            parts.append(f"- {p.get('name', '')} ({p.get('category', '')}) {rating_str}")
            if p.get('address'):
                parts.append(f"  地址: {p['address']}")

    # 住宿数据
    hotels = context.get("hotels", [])
    if hotels:
        parts.append(f"\n## 推荐住宿")
        for h in hotels:
            parts.append(f"- {h.get('name', '')} ({h.get('rating', '?')}分)")
            if h.get('address'):
                parts.append(f"  地址: {h['address']}")
        parts.append("请优先选用以上推荐住宿，并为行程每天安排合适的住宿活动（accommodation）。")

    # 知识库攻略
    knowledge = context.get("knowledge", [])
    if knowledge:
        parts.append(f"\n## 知识库攻略（来自已有旅行攻略，优先参考）")
        for k in knowledge:
            parts.append(f"\n### {k.get('title', '攻略')} (相关度: {k.get('score', 0):.2f})")
            parts.append(k.get("text", ""))

    # 预算信息
    budget = context.get("budget", {})
    if budget:
        breakdown = budget.get("breakdown", {})
        parts.append(f"\n## 预算概览")
        parts.append(f"- 总预算: {breakdown.get('total', '?')} 元")
        parts.append(f"- 人均: {budget.get('per_person', '?')} 元")
        parts.append(f"- 住宿: {breakdown.get('accommodation', 0)} 元")
        parts.append(f"- 餐饮: {breakdown.get('food', 0)} 元")
        parts.append(f"- 交通: {breakdown.get('transport', 0)} 元")
        parts.append(f"- 门票: {breakdown.get('attractions', 0)} 元")

    # 精调反馈
    if refine_feedback:
        parts.append(f"\n## 用户修改意见（请根据以下反馈调整行程）")
        parts.append(refine_feedback)

    # 之前的验证错误
    if validation_errors:
        parts.append(f"\n## 上次行程的问题（请避免再次出现）")
        for err in validation_errors:
            parts.append(f"- {err}")

    return "\n".join(parts)


def _generate_fallback(request: Any, context: dict, refine_feedback: str | None) -> Itinerary:
    """降级方案：基于真实 context 数据生成行程。"""
    days: list[DayPlan] = []
    current_date = request.start_date
    pois = context.get("pois", [])
    weather = context.get("weather", [])

    while current_date <= request.end_date:
        # 获取当天的天气
        day_weather = "晴"
        for w in weather:
            if w.get("date") == current_date.isoformat():
                day_weather = w.get("condition", "晴")
                break

        # 从 POI 中选取当天的景点、美食、购物
        attractions = [p for p in pois if p.get("category") in ("景点", "自然", "历史")]
        foods = [p for p in pois if p.get("category") in ("美食", "餐饮")]
        shops = [p for p in pois if p.get("category") in ("购物",)]

        time_slots = [
            TimeSlot(
                start_time=datetime.time(8, 0),
                end_time=datetime.time(9, 0),
                activity_name="酒店早餐",
                activity_type="food",
                location=Location(
                    name=f"{request.destination}市中心酒店",
                    lat=sum(p.get("lat", 0) for p in pois[:3]) / max(len(pois[:3]), 1) if pois else 35.6762,
                    lng=sum(p.get("lng", 0) for p in pois[:3]) / max(len(pois[:3]), 1) if pois else 139.6503,
                    rating=4.0,
                ),
                cost=0,
                notes="享受酒店自助早餐，补充一天能量",
            ),
        ]

        # 上午：景点
        if attractions:
            idx = (current_date.day - request.start_date.day) % len(attractions)
            a = attractions[idx]
            time_slots.append(TimeSlot(
                start_time=datetime.time(9, 30),
                end_time=datetime.time(12, 0),
                activity_name=f"游览 {a.get('name', '当地景点')}",
                activity_type="attraction",
                location=Location(
                    name=a.get("name", ""),
                    lat=a.get("lat", 0),
                    lng=a.get("lng", 0),
                    address=a.get("address", ""),
                    rating=a.get("rating", 4.0),
                ),
                cost=80,
                notes=f"上午游览最佳，{day_weather}天气适合出游",
            ))
        else:
            time_slots.append(TimeSlot(
                start_time=datetime.time(9, 30),
                end_time=datetime.time(12, 0),
                activity_name=f"探索{request.destination}市区",
                activity_type="attraction",
                location=Location(
                    name=request.destination,
                    lat=35.6762,
                    lng=139.6503,
                    rating=4.0,
                ),
                cost=60,
                notes="自由漫步，感受当地风情",
            ))

        # 午餐
        if foods:
            idx = (current_date.day) % len(foods)
            f = foods[idx]
            time_slots.append(TimeSlot(
                start_time=datetime.time(12, 0),
                end_time=datetime.time(13, 30),
                activity_name=f"午餐 — {f.get('name', '当地美食')}",
                activity_type="food",
                location=Location(
                    name=f.get("name", ""),
                    lat=f.get("lat", 0),
                    lng=f.get("lng", 0),
                    address=f.get("address", ""),
                    rating=f.get("rating", 4.0),
                ),
                cost=80,
                notes="品尝当地特色美食",
            ))
        else:
            time_slots.append(TimeSlot(
                start_time=datetime.time(12, 0),
                end_time=datetime.time(13, 30),
                activity_name=f"午餐 — {request.destination}特色美食",
                activity_type="food",
                location=Location(
                    name=f"{request.destination}美食街",
                    lat=35.6938,
                    lng=139.7036,
                    rating=4.3,
                ),
                cost=80,
                notes="推荐尝试当地招牌菜",
            ))

        # 下午：购物或自由活动
        if shops and current_date.day % 2 == 0:
            idx = (current_date.day // 2) % len(shops)
            s = shops[idx]
            time_slots.append(TimeSlot(
                start_time=datetime.time(14, 30),
                end_time=datetime.time(17, 0),
                activity_name=f"购物 — {s.get('name', '当地商圈')}",
                activity_type="shopping",
                location=Location(
                    name=s.get("name", ""),
                    lat=s.get("lat", 0),
                    lng=s.get("lng", 0),
                    address=s.get("address", ""),
                    rating=s.get("rating", 4.0),
                ),
                cost=200,
                notes="自由购物，注意比价",
            ))
        else:
            time_slots.append(TimeSlot(
                start_time=datetime.time(14, 30),
                end_time=datetime.time(17, 0),
                activity_name=f"{request.destination}自由探索",
                activity_type="other",
                location=Location(
                    name=f"{request.destination}市区",
                    lat=35.6762,
                    lng=139.6503,
                    rating=4.2,
                ),
                cost=100,
                notes="根据个人兴趣自由安排下午行程",
            ))

        # 晚餐
        time_slots.append(TimeSlot(
            start_time=datetime.time(18, 0),
            end_time=datetime.time(20, 0),
            activity_name="晚餐",
            activity_type="food",
                location=Location(
                    name=f"{request.destination}推荐餐厅",
                    lat=35.6762,
                    lng=139.6503,
                    rating=4.5,
                ),
            cost=120,
            notes="热门餐厅建议提前预约",
        ))

        days.append(DayPlan(date=current_date, time_slots=time_slots))
        current_date += datetime.timedelta(days=1)

    tips = [
        f"{request.destination}公共交通便利，建议购买交通卡",
        "热门景点建议提前在线购票，避免排队",
        f"当地天气多变（{day_weather}），建议随身携带雨具",
        "品尝当地美食时注意饮食卫生",
    ]

    itinerary = Itinerary(
        days=days,
        total_budget_estimate=0.0,
        tips=tips,
    )
    _recalculate_budget(itinerary, request.travelers)
    return itinerary
