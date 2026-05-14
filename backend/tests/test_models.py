"""数据模型单元测试"""

import datetime
import pytest
from src.models import (
    TravelRequest,
    Itinerary,
    DayPlan,
    TimeSlot,
    ActivityType,
    Location,
    Settings,
    Pace,
)


def test_travel_request_full():
    """完整参数创建 TravelRequest"""
    req = TravelRequest(
        destination="东京",
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 5),
        travelers=2,
        budget_amount=5000,
        pace="relaxed",
        interests=["美食", "历史"],
        dietary_restrictions=["素食"],
    )
    assert req.destination == "东京"
    assert req.travelers == 2
    assert req.budget_amount == 5000
    assert len(req.interests) == 2


def test_travel_request_defaults():
    """默认值测试"""
    req = TravelRequest(
        destination="巴黎",
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 3),
    )
    assert req.travelers == 1  # 默认值
    assert req.budget_amount is None  # 默认不填
    assert req.pace == "moderate"
    assert req.interests == []
    assert req.dietary_restrictions == []


def test_travel_request_validation():
    """边界校验"""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        TravelRequest(
            destination="",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 3),
            travelers=0,  # ge=1 会失败
        )


def test_location():
    """地理位置模型"""
    loc = Location(name="埃菲尔铁塔", address="Champ de Mars, Paris", lat=48.8584, lng=2.2945, rating=4.7)
    assert loc.lat == 48.8584
    assert loc.rating == 4.7


def test_location_validation():
    """经纬度边界校验"""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        Location(name="invalid", lat=100, lng=200)


def test_time_slot():
    """时间段模型"""
    slot = TimeSlot(
        start_time=datetime.time(9, 0),
        end_time=datetime.time(12, 0),
        activity_name="卢浮宫参观",
        activity_type="attraction",
        cost=120,
    )
    assert slot.activity_type == "attraction"
    assert slot.cost == 120
    assert slot.notes == ""  # 默认值


def test_day_plan():
    """单日计划"""
    loc = Location(name="卢浮宫", lat=48.8606, lng=2.3376, rating=4.8)
    slot = TimeSlot(
        start_time=datetime.time(9, 0),
        end_time=datetime.time(12, 0),
        activity_name="卢浮宫",
        activity_type="attraction",
        location=loc,
        cost=120,
    )
    day = DayPlan(date=datetime.date(2026, 7, 1), time_slots=[slot])
    assert len(day.time_slots) == 1
    assert day.time_slots[0].location is not None
    assert day.time_slots[0].location.name == "卢浮宫"


def test_itinerary():
    """完整行程"""
    slot = TimeSlot(
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        activity_name="早餐",
        activity_type="food",
        cost=50,
    )
    day = DayPlan(date=datetime.date(2026, 7, 1), time_slots=[slot])
    itinerary = Itinerary(
        days=[day],
        total_budget_estimate=1000.0,
        tips=["提前订票"],
    )
    assert len(itinerary.days) == 1
    assert itinerary.total_budget_estimate == 1000.0
    assert len(itinerary.tips) == 1


def test_settings():
    """配置模型"""
    import os

    os.environ["AMAP_API_KEY"] = "test_amap_key"
    os.environ["DEEPSEEK_API_KEY"] = "ds_test_key"
    os.environ["CLAUDE_API_KEY"] = "claude_test"
    os.environ["LLM_PROVIDER"] = "deepseek"
    settings = Settings()
    assert settings.amap_api_key == "test_amap_key"
    assert settings.deepseek_api_key == "ds_test_key"
    assert settings.claude_api_key == "claude_test"
    assert settings.llm_provider == "deepseek"
    assert hasattr(settings, "debug")
