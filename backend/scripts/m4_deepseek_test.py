"""M4 真实端到端测试：Self-Loop 循环 + 审校评分 + 事实核查 + 基准覆盖度。

运行：cd backend && python scripts/m4_deepseek_test.py
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
from app.benchmark.service import compute_coverage  # noqa: E402
from app.presets.research import register_research_preset  # noqa: E402
from app.verification.rules import rule_check  # noqa: E402
from app.workflow.runner import run_workflow  # noqa: E402

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

    # 3) 运行完整工作流（含 Self-Loop + 验证）
    state, events = await run_workflow("research_report",
                                       {"topic": "多智能体系统的工作流编排技术", "kb_id": kb_id},
                                       get_agent_registry(), get_workflow_registry())

    draft = state.get("draft") or ""
    verification = state.get("verification") or {}
    print("=== Self-Loop 评分曲线 ===")
    print(state.get("quality_loop_score_curve"))
    print("\n=== 规则核查 ===")
    print(rule_check(draft))
    print("\n=== 事实核查（verifier）===")
    print("通过率:", verification.get("verification_score"))
    print("有据断言数:", len(verification.get("verified_claims", [])))
    print("无据断言数:", len(verification.get("unsupported_claims", [])))

    # 4) 基准覆盖度（用 golden points 量化，避免重复跑工作流）
    golden_points = ["工作流编排", "动态调度", "自我循环", "任务分解", "角色分工", "冲突消解"]
    score, covered, missing = compute_coverage(draft, golden_points)
    print("\n=== 基准覆盖度 ===")
    print(f"覆盖率: {score}（{len(covered)}/{len(golden_points)}）")
    print("覆盖要点:", covered)
    print("缺失要点:", missing)


if __name__ == "__main__":
    asyncio.run(main())
