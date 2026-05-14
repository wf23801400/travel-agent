"""用户旅行请求数据模型。"""

import datetime
from typing import Literal

from pydantic import BaseModel, Field

Pace = Literal["relaxed", "moderate", "intensive"]


class TravelRequest(BaseModel):
    """用户提交的旅行计划请求。"""

    origin: str = Field(default="", description="出发地", examples=["北京", "上海站"])
    destination: str = Field(..., description="旅行目的地", examples=["东京", "故宫", "张家界国家森林公园"])
    start_date: datetime.date = Field(..., description="行程开始日期")
    end_date: datetime.date = Field(..., description="行程结束日期")
    travelers: int = Field(default=1, ge=1, description="旅行人数")
    budget_amount: float | None = Field(default=None, ge=0, description="预算总额（元），不填则自动估算")
    pace: Pace = Field(default="moderate", description="行程节奏")
    interests: list[str] = Field(
        default_factory=list,
        description="兴趣标签，如美食、历史、自然、购物",
        examples=[["美食", "历史", "购物"]],
    )
    dietary_restrictions: list[str] = Field(
        default_factory=list,
        description="饮食限制，如素食、无麸质",
    )
