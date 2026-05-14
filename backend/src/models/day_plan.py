"""单日计划与时间段数据模型。"""

import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .location import Location

ActivityType = Literal[
    "transport", "accommodation", "food", "attraction", "shopping", "rest", "other"
]


class TimeSlot(BaseModel):
    """单个时间段内的活动安排。"""

    start_time: datetime.time = Field(..., description="活动开始时间")
    end_time: datetime.time = Field(..., description="活动结束时间")
    activity_name: str = Field(..., description="活动名称")
    activity_type: ActivityType = Field(..., description="活动类型")
    location: Optional[Location] = Field(default=None, description="活动地点")
    cost: float = Field(default=0.0, ge=0, description="预估花费")
    notes: str = Field(default="", description="备注信息")


class DayPlan(BaseModel):
    """一天的完整行程计划。"""

    date: datetime.date = Field(..., description="日期")
    time_slots: list[TimeSlot] = Field(
        default_factory=list, description="当天的活动时间段列表"
    )
