"""预算估算节点。"""

from src.tools import BudgetInput, estimate_budget

from ..state import TravelAgentState


async def estimate_budget_node(state: TravelAgentState) -> dict:
    """调用 budget_estimator.estimate_budget 估算旅行预算。"""
    request = state.get("request")
    if request is None:
        return {"budget_data": None}

    days = (request.end_date - request.start_date).days + 1
    budget_input = BudgetInput(
        destination=request.destination,
        travelers=request.travelers,
        days=days,
        budget_amount=request.budget_amount,
    )
    budget_data = await estimate_budget(budget_input)
    return {"budget_data": budget_data}
