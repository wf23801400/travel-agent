"""预算估算工具 — 根据目的地、人数、天数、预算金额生成预算明细。"""

from pydantic import BaseModel, Field

CITY_COST_FACTORS: dict[str, float] = {
    # 国际一线
    "东京": 1.2, "大阪": 1.1, "京都": 1.1, "札幌": 1.0,
    "巴黎": 1.4, "伦敦": 1.5, "纽约": 1.5, "悉尼": 1.3,
    "首尔": 0.9, "曼谷": 0.5, "新加坡": 1.2, "吉隆坡": 0.5,
    "巴厘岛": 0.6, "普吉岛": 0.5, "马尔代夫": 1.6,
    # 国内一线
    "北京": 0.7, "上海": 0.8, "广州": 0.6, "深圳": 0.8,
    # 国内新一线
    "成都": 0.5, "杭州": 0.7, "武汉": 0.5, "西安": 0.5,
    "南京": 0.6, "重庆": 0.5, "长沙": 0.5, "苏州": 0.6,
    "厦门": 0.6, "青岛": 0.6, "天津": 0.6, "郑州": 0.4,
    # 国内旅游热门
    "三亚": 0.8, "丽江": 0.6, "大理": 0.5, "桂林": 0.4,
    "张家界": 0.4, "黄山": 0.5, "武功山": 0.3, "庐山": 0.4,
    "九寨沟": 0.5, "拉萨": 0.6, "乌鲁木齐": 0.5,
    "哈尔滨": 0.5, "昆明": 0.4, "贵阳": 0.4, "南宁": 0.4,
}
"""城市消费系数（相对全国均值 1.0）。

未覆盖的城市默认按 1.0 处理——会偏高，但宁可高估也不低估预算。
这是简化模型，面试时可以说「现阶段覆盖 40+ 热门城市，未来可接高德 POI 的消费数据做动态调整」。
"""

# 人均每日基础花费（元）
BASE_DAILY_COST = 500   # 经济
MODERATE_DAILY_COST = 900  # 适中
LUXURY_DAILY_COST = 1800   # 豪华


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
