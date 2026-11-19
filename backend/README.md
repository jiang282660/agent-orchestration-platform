# Agent 编排调度平台 · 后端（M1）

## 目录结构

```
backend/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置（pydantic-settings）+ LLM 工厂
│   ├── core/
│   │   ├── state.py            # RunState 共享运行状态
│   │   ├── tool.py             # Tool 定义 + ToolRegistry
│   │   ├── llm/                # LLM 网关（base / deepseek / mock）
│   │   └── agent/              # Agent 基类（ReAct 循环）+ AgentRegistry
│   ├── tools/builtin.py        # 内置工具（calculator / get_current_time）
│   └── api/                    # API 路由（health / agents）
├── scripts/smoke_test.py       # 离线冒烟测试（无需网络/API key）
├── requirements.txt
└── .env.example
```

## 快速开始

### 1. 安装依赖（建议虚拟环境）

```bash
cd backend
python -m venv .venv
# Windows (Git Bash):
source .venv/Scripts/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY；或先设 LLM_PROVIDER=mock 离线体验
```

### 3. 离线冒烟测试（无需依赖/网络，验证 ReAct 循环）

```bash
python scripts/smoke_test.py
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --port 8000
# 交互式文档： http://127.0.0.1:8000/docs
```

## API 示例

```bash
# 健康检查
curl http://127.0.0.1:8000/healthz

# 注册一个带工具的计算 Agent
curl -X POST http://127.0.0.1:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{"id":"calc","name":"计算助手","role_prompt":"你是计算助手，用户问算式时用 calculator 工具。","tool_names":["calculator"]}'

# 运行 Agent（ReAct 循环）
curl -X POST http://127.0.0.1:8000/api/agents/calc/run \
  -H "Content-Type: application/json" \
  -d '{"task":"(3+5)*2 等于多少？"}'
```
