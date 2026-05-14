# ✈️ Travel Agent — AI 智能旅游规划师

> 输入目的地 + 偏好，AI 自动生成个性化行程：每日时间线、地图路线、预算估算。

## 🎯 功能

- **智能行程生成**：输入目的地、日期、预算、兴趣标签，AI 集成高德地图实时数据生成行程
- **SSE 流式反馈**：规划过程实时推送进度（解析坐标 → 查天气 → 搜景点 → 算预算 → AI 生成 → 校验）
- **交互式地图**：Leaflet 地图显示每日路线，按天分色标注景点
- **预算估算**：基于高德距离数据 + 城市消费系数 + 天数人数自动计算
- **偏好定制**：节奏（轻松/适中/紧凑）、兴趣（美食/户外/自然/历史/购物）、饮食限制

## 🏗️ 架构

```
用户输入 → FastAPI → LangGraph 流水线 → LLM 推理 → 结构化行程
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 高德地图   DeepSeek   React
 实时数据   AI 推理   前端界面
```

### LangGraph 节点流水线

```
parse_input → fetch_weather → search_poi → estimate_budget → assemble_context → llm_plan → validate_output
                                                                                      ↑        │
                                                                                      └─retry─┘（最多 2 次）
```

## 🛠️ 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.12 · FastAPI · LangGraph · Pydantic v2 |
| 前端 | React 19 · Vite 8 · TypeScript 6 · Tailwind CSS 4 · Leaflet |
| 外部 API | 高德地图（地理编码/POI/天气/路线）· DeepSeek（LLM 推理） |
| 测试 | pytest · pytest-asyncio · pytest-mock |

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/wf23801400/travel-agent.git
cd travel-agent
```

### 2. 配置 API Key

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入你的高德和 DeepSeek API key
```

| Key | 获取地址 |
|-----|---------|
| `AMAP_API_KEY` | https://console.amap.com/ |
| `DEEPSEEK_API_KEY` | https://platform.deepseek.com/ |

### 3. 启动后端

```powershell
cd backend
pip install -r requirements.txt
python main.py
# → http://localhost:8000/docs
```

### 4. 启动前端

```powershell
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## 📡 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/plan` | POST | 生成行程（同步） |
| `/api/plan/stream` | POST | 生成行程（SSE 流式，带进度） |
| `/api/plan/refine` | POST | 根据反馈优化行程 |
| `/api/health` | GET | 健康检查 |

### 请求示例

```json
POST /api/plan/stream
{
  "destination": "武功山",
  "start_date": "2026-05-16",
  "end_date": "2026-05-18",
  "travelers": 1,
  "budget_amount": 2000,
  "pace": "moderate",
  "interests": ["美食", "户外", "自然"]
}
```

### SSE 事件

```
event: progress       → {"step": "fetch_weather", "label": "🌤️ 正在查询当地天气..."}
event: progress       → {"step": "llm_plan", "label": "🧠 AI 正在生成个性化行程..."}
event: complete       → {"itinerary": {...}}
event: error          → {"step": "...", "error": "..."}
```

## 📁 目录结构

```
travel-agent/
├── backend/
│   ├── src/
│   │   ├── api/          # FastAPI 路由
│   │   ├── graph/        # LangGraph 图（nodes/edges/state）
│   │   ├── models/       # Pydantic 数据模型
│   │   ├── services/     # 高德 API 客户端 & LLM 客户端
│   │   └── tools/        # 工具函数（天气/POI/地理/路线/预算）
│   ├── tests/
│   └── main.py           # 入口
├── frontend/
│   └── src/
│       ├── api/          # 后端 API 调用封装
│       └── components/   # React 组件（地图/时间线/表单/预算）
├── CLAUDE.md             # Claude Code 项目上下文
└── .env.example          # 环境变量模板
```

## 🧪 测试

```bash
cd backend
pip install -r tests/requirements.txt
pytest tests/ -v
```
