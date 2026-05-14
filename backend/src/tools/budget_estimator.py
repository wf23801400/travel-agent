"""预算估算工具 — 根据目的地、人数、天数、预算金额生成预算明细。"""

from pydantic import BaseModel, Field

CITY_COST_FACTORS: dict[str, float] = {
    "东京": 1.2,
    "大阪": 1.1,
    "巴黎": 1.4,
    "纽约": 1.5,
    "曼谷": 0.5,
    "北京": 0.7,
    "上海": 0.8,
    "广州": 0.6,
    "成都": 0.5,
}

# 人均每日基础花费（元）
BASE_DAILY_COST = 500  # 经济
MODERATE_DAILY_COST = 900  # 适中
LUXURY_DAILY_COST = 1800  # 豪华


class BudgetInput(BaseModel):
    """预算估算输入。"""

    destination: str = Field(..., description="目的地", examples=["东京"])
    travelers: int = Field(..., ge=1, description="旅行人数")
    days: int = Field(..., ge=1, description="旅行天数")
    budget_amount: float | None = Field(default=None, ge=0, description="预算总额（元），不填则自动按适中档估算")
    currency: str = Field(default="CNY", description="货币代码")


class BudgetBreakdown(BaseModel):
    """分项预算明细。"""

    accommodation: float = Field(..., ge=0, description="住宿费用")
    food: float = Field(..., ge=0, description="餐饮费用")
    transport: float = Field(..., ge=0, description="交通费用")
    attractions: float = Field(..., ge=0, description="景点门票/活动费用")
    shopping: float = Field(..., ge=0, description="购物费用")
    misc: float = Field(..., ge=0, description="杂项/保险/签证等")
    total: float = Field(..., ge=0, description="总计")


class BudgetOutput(BaseModel):
    """预算估算输出。"""

    destination: str = Field(..., description="目的地")
    breakdown: BudgetBreakdown = Field(..., description="分项预算明细")
    currency: str = Field(..., description="货币代码")
    per_person: float = Field(..., ge=0, description="人均预算")


async def estimate_budget(params: BudgetInput) -> BudgetOutput:
    """根据参数估算旅行预算。

    - 如果用户指定了 budget_amount，以用户预算为准分配各项比例
    - 否则按适中档自动估算
    """
    try:
        city_factor = CITY_COST_FACTORS.get(params.destination, 1.0)

        if params.budget_amount and params.budget_amount > 0:
            # 用户指定的预算总额
            total = params.budget_amount
        else:
            # 自动估算：适中档 (900/人/天 × 城市系数)
            daily = int(MODERATE_DAILY_COST * city_factor)
            total = params.travelers * params.days * daily

        breakdown = BudgetBreakdown(
            accommodation=round(total * 0.40, 2),
            food=round(total * 0.25, 2),
            transport=round(total * 0.15, 2),
            attractions=round(total * 0.10, 2),
            shopping=round(total * 0.07, 2),
            misc=round(total * 0.03, 2),
            total=round(total, 2),
        )
        return BudgetOutput(
            destination=params.destination,
            breakdown=breakdown,
            currency=params.currency,
            per_person=round(total / params.travelers, 2),
        )
    except Exception:
        return BudgetOutput(
            destination=params.destination,
            breakdown=BudgetBreakdown(
                accommodation=0, food=0, transport=0, attractions=0, shopping=0, misc=0, total=0
            ),
            currency=params.currency,
            per_person=0,
        )
