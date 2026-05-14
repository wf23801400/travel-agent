"""解析用户输入节点 — 校验 TravelRequest 并初始化状态。"""

from ..state import TravelAgentState


async def parse_input(state: TravelAgentState) -> dict:
    """校验 TravelRequest，将 retry_count 置零，进入后续流水线。"""
    request = state.get("request")
    if request is None:
        return {
            "validation_errors": ["TravelRequest 不能为空"],
        }
    errors: list[str] = []
    if not request.destination:
        errors.append("destination 不能为空")
    if request.start_date > request.end_date:
        errors.append("start_date 不能晚于 end_date")
    if request.travelers < 1:
        errors.append("travelers 必须 >= 1")

    return {
        "validation_errors": errors,
        "retry_count": 0,
    }
