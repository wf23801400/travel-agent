# Travel Agent — 生产级旅游规划 Agent

## 项目定位
生产级产品，所有数据通过高德地图 API 获取实时信息。

## 技术栈
- 后端: Python 3.12 + FastAPI + LangGraph + Pydantic v2
- 前端: React + Vite + TypeScript + Tailwind CSS + Leaflet (地图)
- 测试: pytest + pytest-asyncio + pytest-mock
- 外部API: 高德地图 Web API (地理编码、POI搜索、天气、路线规划、静态图)
- LLM: DeepSeek/Claude API (用于行程规划推理)

## 目录结构
```
travel-agent/
├── backend/
│   ├── src/
│   │   ├── models/    # Pydantic 数据模型
│   │   ├── tools/     # 工具函数（天气、POI、地理、路线、预算）
│   │   │   ├── weather_tool.py     # 高德天气API
│   │   │   ├── poi_search.py       # 高德POI搜索
│   │   │   ├── geo_tool.py         # 高德地理编码+坐标转换
│   │   │   ├── route_tool.py       # 高德路径规划
│   │   │   └── budget_estimator.py # 预算估算（基于高德距离+城市系数）
│   │   ├── graph/     # LangGraph 图定义
│   │   │   ├── state.py
│   │   │   ├── nodes/
│   │   │   ├── edges.py
│   │   │   └── graph.py
│   │   ├── api/       # FastAPI 路由
│   │   ├── services/  # 外部API调用封装
│   │   │   ├── amap_client.py     # 高德地图HTTP客户端
│   │   │   └── llm_client.py      # LLM调用封装
│   │   └── prompts/   # LLM system prompt 模板
│   ├── main.py        # 后端入口
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TravelMap.tsx       # Leaflet 地图
│   │   │   ├── ItineraryTimeline.tsx # 时间线
│   │   │   ├── PreferenceForm.tsx  # 偏好表单
│   │   │   └── BudgetSummary.tsx   # 预算总结
│   │   ├── api/client.ts          # 调后端 API
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   ├── test_models.py
│   ├── test_tools.py
│   └── test_graph.py
└── .env.example
```

## 高德 API 集成规范
1. 创建 `src/services/amap_client.py` — 统一的高德 HTTP 客户端，管理 API key、限流、重试、错误处理
2. 所有工具函数通过 `amap_client` 调高德 API，不直接发 HTTP 请求
3. API key 从环境变量 `AMAP_API_KEY` 读取，通过 pydantic-settings 加载
4. 每个 API 调用有 3 次重试 + 指数退避
5. 高德 API 失败时返回结构化错误（不抛异常），前端展示友好提示

## 高德 API 清单
| 接口 | 用途 | 工具 |
|------|------|------|
| 地理编码/逆地理编码 | 城市名转坐标、地址转坐标 | geo_tool.py |
| POI搜索 | 搜索景点/餐厅/酒店/购物 | poi_search.py |
| 天气查询 | 实时天气+未来4天预报 | weather_tool.py |
| 路径规划 | 出发地到目的地交通方案 | route_tool.py |
| 行政区域查询 | 获取城市行政区划 | geo_tool.py |

## LLM 集成规范
1. 创建 `src/services/llm_client.py` — 统一的 LLM 调用封装
2. 支持 DeepSeek (默认) 和 Claude 作为备选
3. 使用 Pydantic response_model 约束结构化输出
4. API key 从环境变量读取: `DEEPSEEK_API_KEY` 或 `CLAUDE_API_KEY`
5. 行程生成调用 LLM 完成，所有上下文数据（天气、POI、路线、预算）作为输入

## 代码规范
- 所有函数写类型注解，Google 风格 docstring
- Pydantic v2 语法，用 response_model 做结构化输出
- 工具函数统一签名: async def tool(params: InputModel) -> OutputModel
- API key 用 pydantic-settings + .env，不硬编码
- 全异步（async/await）
- 任何外部API失败返回结构化兜底数据，不抛异常
- 所有文本用中文

## 分阶段开发进度

### ✅ 阶段1: 数据模型
Pydantic v2 模型: TravelRequest (+origin), Itinerary, DayPlan, TimeSlot, Location, Settings

### ✅ 阶段2: 工具函数（基础版）
weather_tool (mock), poi_search (mock), geo_tool (haversine), budget_estimator (基础系数)

### ✅ 阶段3: LangGraph 图
state.py + nodes + edges + graph.py

### ✅ 阶段4: API + 前端（基础版）
FastAPI + React + Leaflet 地图

### ✅ 阶段5: 测试
pytest 单元测试 + 集成测试

### 🔄 阶段6: 高德 API 集成
- [ ] 创建 amap_client.py — 高德HTTP客户端 (限流、重试)
- [ ] 改造 geo_tool.py — 调用高德地理编码API
- [ ] 改造 weather_tool.py — 调用高德天气API
- [ ] 改造 poi_search.py — 调用高德POI搜索API
- [ ] 新增 route_tool.py — 调用高德路径规划API
- [ ] 创建 llm_client.py — LLM调用封装
- [ ] 改造 llm_plan.py — 用LLM+真实数据生成行程
- [ ] 更新 models 支持新字段
- [ ] 更新 tests

## 质量约束
- LLM 输出必须通过 Pydantic response_model 验证
- 工具失败返回结构化兜底数据，不抛异常
- 条件边控制重试逻辑（最多2次）
- 所有外部API调用有超时（10s）和重试（3次）
- 高德 API key 缺失时降级使用 mock 数据
