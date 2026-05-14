"""完整行程数据模型。"""

from pydantic import BaseModel, Field

from .day_plan import DayPlan


class Itinerary(BaseModel):
    """由LLM生成的完整旅行行程。"""

    days: list[DayPlan] = Field(default_factory=list, description="每日计划列表")
    total_budget_estimate: float = Field(default=0.0, ge=0, description="总预算估算")
    tips: list[str] = Field(default_factory=list, description="旅行建议/贴士")
