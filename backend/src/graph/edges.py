"""条件边函数 — 控制 LangGraph 图的条件路由。"""

from typing import Literal

from .state import TravelAgentState


def should_retry(state: TravelAgentState) -> Literal["llm_plan", "__end__"]:
    """存在 validation_errors 且重试次数不足时返回 llm_plan，否则结束。"""
    errors = state.get("validation_errors", [])
    retry_count = state.get("retry_count", 0)
    if errors and retry_count < 2:
        return "llm_plan"
    return "__end__"


def has_refine_request(state: TravelAgentState) -> Literal["llm_plan", "__end__"]:
    """存在 refine_feedback 时重新进入 LLM 规划。"""
    if state.get("refine_feedback"):
        return "llm_plan"
    return "__end__"
