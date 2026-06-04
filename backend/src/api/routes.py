"""FastAPI 路由 — /api/plan, /api/plan/refine, /api/plan/stream, /api/health。"""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.graph.graph import compiled_graph
from src.models import Itinerary, TravelRequest

logger = logging.getLogger(__name__)
router = APIRouter()


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
    """SSE 流式生成行程，通过 LangGraph astream_events 实时推送节点进度。"""

    NODE_LABELS = {
        "parse_input": "📍 正在解析目的地坐标...",
        "search_knowledge": "📚 正在检索旅行攻略...",
        "fetch_weather": "🌤️  正在查询当地天气...",
        "search_poi": "🔍 正在搜索景点和美食...",
        "estimate_budget": "💰 正在估算旅行预算...",
        "assemble_context": "📊 正在整合所有信息...",
        "llm_plan": "🧠 AI 正在生成个性化行程...",
        "validate_output": "✅ 正在校验行程合理性...",
    }

    async def event_stream():
        try:
            async for event in compiled_graph.astream_events(
                {"request": req},
                version="v2",
            ):
                kind = event.get("event")
                if kind == "on_chain_start" and event.get("name") in NODE_LABELS:
                    node_name = event["name"]
                    yield (
                        f"event: progress\n"
                        f"data: {json.dumps({'step': node_name, 'label': NODE_LABELS[node_name]})}\n\n"
                    )
                elif kind == "on_custom_event":
                    yield (
                        f"event: progress\n"
                        f"data: {json.dumps(event.get('data', {}))}\n\n"
                    )
                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event.get("data", {}).get("output", {})
                    itinerary = output.get("itinerary")
                    if itinerary is None:
                        yield f"event: error\ndata: {json.dumps({'step': 'done', 'error': '行程生成失败'})}\n\n"
                        return
                    yield (
                        f"event: complete\n"
                        f"data: {json.dumps({'itinerary': itinerary.model_dump(mode='json')})}\n\n"
                    )
        except Exception as e:
            logger.error("流式生成失败: %s", str(e))
            yield f"event: error\ndata: {json.dumps({'step': 'graph', 'error': str(e)})}\n\n"

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
