"""知识检索节点 — 根据用户查询从知识库检索攻略片段。"""

from src.tools.knowledge_retriever import retrieve_knowledge

from ..state import TravelAgentState


async def search_knowledge(state: TravelAgentState) -> dict:
    """从攻略知识库检索相关片段。

    从用户请求中提取查询文本，检索最相关的攻略片段。
    结果存入 state.knowledge_results。
    """
    request = state.get("request")
    if request is None:
        return {"knowledge_results": []}

    # 构造查询：目的地 + 兴趣 + 预算
    query_parts = [request.destination]
    if request.interests:
        query_parts.extend(request.interests)
    if request.budget_amount and request.budget_amount < 1000:
        query_parts.append("省钱 穷游")

    query = " ".join(query_parts)

    try:
        results = await retrieve_knowledge(query, k=3)
    except Exception:
        results = []

    return {"knowledge_results": results}
