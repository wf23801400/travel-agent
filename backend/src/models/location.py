"""地理位置数据模型。"""

from typing import Optional

from pydantic import BaseModel, Field


class Location(BaseModel):
    """地点信息，用于地图展示和POI标注。"""

    name: str = Field(..., description="地点名称")
    address: str = Field(default="", description="详细地址")
    lat: float = Field(..., ge=-90, le=90, description="纬度")
    lng: float = Field(..., ge=-180, le=180, description="经度")
    rating: Optional[float] = Field(default=None, ge=0, le=5, description="评分 (0-5)")
