"""LangGraph 图组装 — 注册所有节点和边，导出 compiled graph。"""

from langgraph.graph import END, START, StateGraph

from .edges import has_refine_request, should_retry
from .nodes.assemble_context import assemble_context
from .nodes.estimate_budget import estimate_budget_node
from .nodes.fetch_weather import fetch_weather
from .nodes.llm_plan import llm_plan
from .nodes.parse_input import parse_input
from .nodes.search_poi import search_poi
from .nodes.validate_output import validate_output
from .state import TravelAgentState

builder = StateGraph(TravelAgentState)

# 注册节点
builder.add_node("parse_input", parse_input)
builder.add_node("fetch_weather", fetch_weather)
builder.add_node("search_poi", search_poi)
builder.add_node("estimate_budget", estimate_budget_node)
builder.add_node("assemble_context", assemble_context)
builder.add_node("llm_plan", llm_plan)
builder.add_node("validate_output", validate_output)

# 编排边
builder.add_edge(START, "parse_input")
builder.add_edge("parse_input", "fetch_weather")
builder.add_edge("fetch_weather", "search_poi")
builder.add_edge("search_poi", "estimate_budget")
builder.add_edge("estimate_budget", "assemble_context")
builder.add_edge("assemble_context", "llm_plan")
builder.add_edge("llm_plan", "validate_output")

# 条件边: 校验失败且未超过重试次数时回到 llm_plan
builder.add_conditional_edges(
    "validate_output",
    should_retry,
    {
        "llm_plan": "llm_plan",
        "__end__": END,
    },
)

compiled_graph = builder.compile()
