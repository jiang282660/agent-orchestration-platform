"""完整演示：入库样例资料 → 运行研究报告工作流 → 输出评分曲线/验证/覆盖度。

运行：cd backend && python scripts/demo.py
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

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"
TOPIC = "多智能体系统的工作流编排技术"


async def main():
    svc = get_kb_service()
    # 1) 找或建演示知识库，入库所有样例文档
    kb_id = next((k["id"] for k in svc.list_kbs() if k["name"] == "演示知识库"), None)
    if not kb_id:
        kb_id = svc.create_kb("演示知识库", "多智能体与工作流编排资料").id
    existing = {d["filename"] for d in svc.list_documents(kb_id)}
    for f in sorted(SAMPLES.glob("*.md")):
        if f.name not in existing:
            svc.add_document(kb_id, f.name, f.read_bytes())
            print("入库样例:", f.name)
    print("知识库文档数:", len(svc.list_documents(kb_id)))

    # 2) 预置团队 + 工作流并运行
    register_research_preset(get_agent_registry(), get_tool_registry(), get_workflow_registry(), get_llm())
    state, _ = await run_workflow("research_report", {"topic": TOPIC, "kb_id": kb_id},
                                  get_agent_registry(), get_workflow_registry())

    draft = state.get("draft") or ""
    verification = state.get("verification") or {}
    kb = svc.get_kb(kb_id)
    print("知识库检索:", kb.retriever_type, "| 语义向量:", "已启用" if kb.retriever.semantic_available() else "未启用（降级 BM25）")
    print("\n=== Self-Loop 评分曲线 ===")
    print(state.get("quality_loop_score_curve"))
    print("\n=== 规则核查（工作流 rule_gate 节点）===")
    print(state.get("rule_check") or rule_check(draft))
    print("\n=== 事实核查 ===")
    print("通过率:", verification.get("verification_score"),
          "| 有据:", len(verification.get("verified_claims", [])),
          "| 无据:", len(verification.get("unsupported_claims", [])))

    golden = ["工作流编排", "动态调度", "自我循环", "任务分解", "角色分工", "冲突消解", "合同网协议", "事实核查", "基准集", "DAG"]
    score, covered, missing = compute_coverage(draft, golden)
    print("\n=== 基准覆盖度 ===")
    print(f"{score}（{len(covered)}/{len(golden)}）缺失: {missing}")

    print("\n=== 报告初稿（前 800 字）===")
    print(draft[:800])


if __name__ == "__main__":
    asyncio.run(main())
