"""行程校验节点 — 检查 Itinerary 是否包含必填字段。"""

from ..state import TravelAgentState


async def validate_output(state: TravelAgentState) -> dict:
    """校验 Itinerary 数据完整性，错误写入 validation_errors。"""
    itinerary = state.get("itinerary")
    errors: list[str] = []

    if itinerary is None:
        errors.append("itinerary 为空，LLM 未能生成行程")
        return {"validation_errors": errors}

    if not itinerary.days:
        errors.append("itinerary.days 为空，至少需要一个 DayPlan")

    for i, day in enumerate(itinerary.days):
        if not day.time_slots:
            errors.append(f"Day {i} ({day.date}): time_slots 为空")
            continue
        for j, slot in enumerate(day.time_slots):
            if slot.start_time >= slot.end_time:
                errors.append(
                    f"Day {i} Slot {j}: start_time ({slot.start_time}) >= end_time ({slot.end_time})"
                )
            if not slot.activity_name:
                errors.append(f"Day {i} Slot {j}: activity_name 为空")

    return {"validation_errors": errors}
