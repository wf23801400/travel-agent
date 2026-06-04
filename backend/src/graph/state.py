"""LangGraph 状态定义。"""

from typing import TypedDict

from src.models import Itinerary, TravelRequest
from src.tools import BudgetOutput, POISearchOutput, WeatherOutput


class TravelAgentState(TypedDict, total=False):
    """旅行规划 Agent 的全局状态。

    所有字段默认 None/空列表，节点通过返回 dict 增量更新。
    """

    request: TravelRequest | None
    weather_data: WeatherOutput | None
    poi_data: POISearchOutput | None
    budget_data: BudgetOutput | None
    context: dict | None
    itinerary: Itinerary | None
    validation_errors: list[str]
    retry_count: int
    refine_feedback: str | None
    knowledge_results: list[dict]
