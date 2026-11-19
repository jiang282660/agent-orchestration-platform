"""真实 DeepSeek 工作流端到端测试：研究报告生成全流程。

运行：cd backend && python scripts/workflow_deepseek_test.py
"""

import asyncio
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.deps import (  # noqa: E402
    get_agent_registry,
    get_kb_service,
    get_llm,
    get_tool_registry,
    get_workflow_registry,
)
from app.core.state import RunState  # noqa: E402
from app.presets.research import register_research_preset  # noqa: E402
from app.workflow.dsl import iter_nodes  # noqa: E402
from app.workflow.engine import WorkflowEngine  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples" / "ai_agents_intro.md"


async def main():
    # 1) 知识库准备
    svc = get_kb_service()
    kb_id = next((k["id"] for k in svc.list_kbs() if k["name"] == "AI 智能体资料库"), None)
    if not kb_id:
        kb_id = svc.create_kb("AI 智能体资料库", "演示知识库").id
    if not svc.list_documents(kb_id):
        svc.add_document(kb_id, SAMPLE.name, SAMPLE.read_bytes())

    # 2) 预置团队 + 工作流
    register_research_preset(get_agent_registry(), get_tool_registry(), get_workflow_registry(), get_llm())
    spec = get_workflow_registry().get("research_report")

    agents = {}
    for n in iter_nodes(spec):
        if n.agent and n.agent not in agents:
            agents[n.agent] = get_agent_registry().get(n.agent)

    # 3) 运行
    engine = WorkflowEngine(agents)
    state = RunState({"topic": "多智能体系统的工作流编排技术", "kb_id": kb_id})
    await engine.run(spec, state)

    print("=== 研究大纲 ===")
    print(state.get("outline"))
    print("\n=== 子任务数:", len(state.get("subtasks", [])))
    print("=== 分析结果数:", len(state.get("analyses", [])))
    print("\n=== 报告初稿 ===")
    print(state.get("draft"))


if __name__ == "__main__":
    asyncio.run(main())
