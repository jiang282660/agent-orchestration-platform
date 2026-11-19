# 大模型 Agent 工具编排调度平台

面向多智能体协作的编排、调度、执行与验证平台，对标 LobeHub / DeepSeek Harness。
业务场景：**基于知识库的多智能体研究报告生成**。

完整技术方案见 [`docs/技术方案.md`](docs/技术方案.md)。

## 目录结构

```
├── docs/技术方案.md         # 架构设计与技术方案
├── backend/                 # Python + FastAPI 后端
│   ├── app/
│   │   ├── core/            # Agent 基类(ReAct)、Tool、RunState、LLM 网关
│   │   ├── kb/              # 知识库（解析/分块/BM25 检索）
│   │   ├── workflow/        # 工作流引擎（DAG/expand/loop）+ 运行器
│   │   ├── verification/    # 规则核查
│   │   ├── benchmark/       # 基准集（golden set）
│   │   ├── presets/         # 预置六角色团队 + 研究报告工作流
│   │   └── api/routes/      # kb/agents/workflows/runs/benchmarks 路由
│   └── scripts/             # 各模块冒烟/端到端测试
└── frontend/                # Vue3 + Element Plus + Vite 前端
```

## 快速开始

### 1. 后端

```bash
cd backend
source .venv/Scripts/activate          # 已建好虚拟环境（Windows Git Bash）
# 若 .env 未配置，复制 .env.example 并填入 DEEPSEEK_API_KEY
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. 前端（另开一个终端）

```bash
cd frontend
npm install       # 已装过可跳过
npm run dev       # 打开 http://127.0.0.1:5173
```

前端通过 Vite 代理将 `/api` 转发到 `http://127.0.0.1:8000`。

## 演示流程

1. **知识库**页：新建知识库 → 上传若干 PDF/Markdown 文档 → 检索验证。
2. **任务运行**页：填写研究主题、选择知识库 → 点「开始运行」→ 实时看板展示
   planner 规划 → 动态扇出并行检索/分析 → Self-Loop 撰写↔审校（评分曲线）→ verifier 事实核查 → 输出报告。
3. **基准评估**页：新建基准集（问题 + 必覆盖要点）→ 运行评估 → 查看覆盖度。

## 后端 API 一览

```
GET   /healthz
POST  /api/kb                        创建知识库
POST  /api/kb/{id}/documents         上传文档
POST  /api/kb/{id}/search            检索
GET   /api/agents                    列出 Agent 团队
GET   /api/workflows                 列出工作流
POST  /api/runs                      创建运行（异步）
GET   /api/runs/{id}/events          SSE 流式执行事件
POST  /api/benchmarks                创建基准集
POST  /api/benchmarks/{id}/run       运行基准评估
```

## 测试脚本

```bash
cd backend
python scripts/smoke_test.py              # ReAct 循环（离线）
python scripts/kb_smoke_test.py           # 知识库链路（离线）
python scripts/workflow_offline_test.py   # DAG + expand（离线）
python scripts/loop_offline_test.py       # Self-Loop（离线）
python scripts/deepseek_test.py           # 真实 DeepSeek（key + function-calling + kb_search）
python scripts/workflow_deepseek_test.py  # 真实研究报告工作流
python scripts/m4_deepseek_test.py        # 真实全流程（loop + 验证 + 基准覆盖度）
python scripts/demo.py                    # 一键演示（入库样例 → 跑工作流 → 出评分/验证/覆盖度）
```
