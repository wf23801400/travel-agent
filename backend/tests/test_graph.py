"""LangGraph 图单元测试"""

import datetime
import pytest
from src.graph.state import TravelAgentState
from src.graph.edges import should_retry, has_refine_request
from src.models import TravelRequest
from src.tools import WeatherOutput, DailyWeather


def make_request() -> TravelRequest:
    return TravelRequest(
        destination="东京",
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 3),
        travelers=2,
        budget_amount=None,
        pace="moderate",
        interests=["美食", "历史"],
    )


def test_should_retry_no_errors():
    """无校验错误 → 结束"""
    state: TravelAgentState = {"validation_errors": [], "retry_count": 0}
    assert should_retry(state) == "__end__"


def test_should_retry_with_errors():
    """有错误且重试次数未超 → 重试"""
    state: TravelAgentState = {"validation_errors": ["itinerary is empty"], "retry_count": 0}
    assert should_retry(state) == "llm_plan"


def test_should_retry_max_retries():
    """重试次数超限 → 结束"""
    state: TravelAgentState = {"validation_errors": ["still broken"], "retry_count": 2}
    assert should_retry(state) == "__end__"


def test_has_refine_request():
    """有 refine_feedback → 重入 LLM"""
    state: TravelAgentState = {"refine_feedback": "把第一天行程改轻松点"}
    assert has_refine_request(state) == "llm_plan"


def test_has_refine_request_none():
    """无 refine_feedback → 结束"""
    state: TravelAgentState = {"refine_feedback": None}
    assert has_refine_request(state) == "__end__"


@pytest.mark.asyncio
async def test_graph_compiled():
    """图能编译成功"""
    from src.graph.graph import compiled_graph
    assert compiled_graph is not None
    assert hasattr(compiled_graph, "ainvoke")


@pytest.mark.asyncio
async def test_graph_full_flow():
    """端到端：请求 → 行程输出"""
    from src.graph.graph import compiled_graph

    req = make_request()
    result = await compiled_graph.ainvoke({"request": req})
    assert result is not None
    assert "itinerary" in result
    assert result["itinerary"] is not None
    assert len(result["itinerary"].days) > 0
    assert result["itinerary"].total_budget_estimate > 0


@pytest.mark.asyncio
async def test_graph_with_refine():
    """带修改反馈的流程"""
    from src.graph.graph import compiled_graph

    req = make_request()
    result = await compiled_graph.ainvoke({
        "request": req,
        "refine_feedback": "增加更多美食推荐",
    })
    assert result["itinerary"] is not None


@pytest.mark.asyncio
async def test_graph_validation_recovery():
    """校验失败 → 自动重试 → 最终输出"""
    from src.graph.graph import compiled_graph

    req = make_request()
    result = await compiled_graph.ainvoke({
        "request": req,
        "validation_errors": ["模拟错误"],
        "retry_count": 0,
    })
    # 重试后应该得到有效行程
    assert result["itinerary"] is not None
