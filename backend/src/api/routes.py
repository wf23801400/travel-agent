"""FastAPI 路由 — /api/plan, /api/plan/refine, /api/plan/stream, /api/health。"""

import asyncio
import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.graph.graph import compiled_graph
from src.models import Itinerary, TravelRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# SSE 进度阶段定义
PROGRESS_STEPS = [
    ("geocode", "📍 正在解析目的地坐标..."),
    ("weather", "🌤️  正在查询当地天气..."),
    ("poi", "🔍 正在搜索景点和美食..."),
    ("budget", "💰 正在估算旅行预算..."),
    ("context", "📊 正在整合所有信息..."),
    ("llm", "🧠 AI 正在生成个性化行程..."),
    ("validate", "✅ 正在校验行程合理性..."),
    ("done", "🎉 行程规划完成！"),
]


@router.post("/api/plan", response_model=Itinerary)
async def plan_travel(req: TravelRequest) -> Itinerary:
    result = await compiled_graph.ainvoke({"request": req})
    return result["itinerary"]


class RefineRequest(BaseModel):
    request: TravelRequest
    feedback: str = Field(..., description="用户反馈/修改意见")


@router.post("/api/plan/refine", response_model=Itinerary)
async def refine_plan(body: RefineRequest) -> Itinerary:
    result = await compiled_graph.ainvoke({
        "request": body.request,
        "refine_feedback": body.feedback,
    })
    return result["itinerary"]


@router.post("/api/plan/stream")
async def plan_travel_stream(req: TravelRequest):
    """SSE 流式生成行程，每个阶段推送进度事件。"""
    from src.graph.nodes.parse_input import parse_input
    from src.graph.nodes.fetch_weather import fetch_weather
    from src.graph.nodes.search_poi import search_poi
    from src.graph.nodes.estimate_budget import estimate_budget_node
    from src.graph.nodes.assemble_context import assemble_context
    from src.graph.nodes.llm_plan import llm_plan
    from src.graph.nodes.validate_output import validate_output
    from src.graph.edges import should_retry
    from src.graph.state import TravelAgentState

    STEPS = [
        ("parse_input", parse_input, "📍 正在解析目的地坐标..."),
        ("fetch_weather", fetch_weather, "🌤️  正在查询当地天气..."),
        ("search_poi", search_poi, "🔍 正在搜索景点和美食..."),
        ("estimate_budget", estimate_budget_node, "💰 正在估算旅行预算..."),
        ("assemble_context", assemble_context, "📊 正在整合所有信息..."),
        ("llm_plan", llm_plan, "🧠 AI 正在生成个性化行程..."),
        ("validate_output", validate_output, "✅ 正在校验行程合理性..."),
    ]

    MAX_RETRIES = 2

    async def event_stream():
        state: TravelAgentState = {"request": req}

        step_index = 0
        while step_index < len(STEPS):
            step_name, step_fn, step_label = STEPS[step_index]

            yield f"event: progress\ndata: {json.dumps({'step': step_name, 'label': step_label})}\n\n"

            try:
                result = await step_fn(state)
                state.update(result)
            except Exception as e:
                logger.error("步骤 %s 失败: %s", step_name, str(e))
                yield f"event: error\ndata: {json.dumps({'step': step_name, 'error': str(e)})}\n\n"
                return

            # 校验步骤后判断是否需要重试
            if step_name == "validate_output":
                retry = should_retry(state)
                retry_count = state.get("retry_count", 0)
                if retry == "llm_plan" and retry_count < MAX_RETRIES:
                    yield f"event: progress\ndata: {json.dumps({'step': 'retry', 'label': f'🔄 行程需要调整（第{retry_count + 1}次重试）...'})}\n\n"
                    # 回退到 llm_plan 步骤
                    step_index = STEPS.index(next(s for s in STEPS if s[0] == "llm_plan"))
                    continue

            step_index += 1

        itinerary = state.get("itinerary")
        if itinerary is None:
            yield f"event: error\ndata: {json.dumps({'step': 'done', 'error': '行程生成失败'})}\n\n"
            return

        # 发送完成事件
        yield f"event: complete\ndata: {json.dumps({'itinerary': itinerary.model_dump(mode='json')})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/health")
async def health():
    return {"status": "ok"}


def setup_cors(app):
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
