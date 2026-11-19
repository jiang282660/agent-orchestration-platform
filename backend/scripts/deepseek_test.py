"""真实 DeepSeek 端到端测试：验证 API key + function-calling + 知识库检索。

运行：cd backend && python scripts/deepseek_test.py
"""

import asyncio
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import build_llm, get_settings  # noqa: E402
from app.core.agent.base import Agent  # noqa: E402
from app.kb.service import KnowledgeBaseService  # noqa: E402
from app.tools.builtin import calculator  # noqa: E402
from app.tools.kb_tool import make_kb_search_tool  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples" / "ai_agents_intro.md"


async def main():
    llm = build_llm(get_settings())

    # 1) function-calling + ReAct 循环
    calc_agent = Agent(
        id="calc", name="计算助手",
        role_prompt="你是计算助手，遇到算式必须用 calculator 工具计算，不要心算。",
        llm=llm, tools=[calculator], max_steps=5,
    )
    r = await calc_agent.run("计算 (3+5)*2 等于多少？")
    print("【calculator】输出:", r.output)
    print("【calculator】工具调用:", [t["name"] for t in r.tool_trace])

    # 2) 知识库 + kb_search 工具
    svc = KnowledgeBaseService()
    kbs = svc.list_kbs()
    kb_id = kbs[0]["id"] if kbs else svc.create_kb("AI 智能体资料库", "演示知识库").id
    if not svc.list_documents(kb_id):
        svc.add_document(kb_id, SAMPLE.name, SAMPLE.read_bytes())
        print("【kb】已入库样例文档:", SAMPLE.name)

    kb_search = make_kb_search_tool(svc)
    retriever = Agent(
        id="retriever", name="检索助手",
        role_prompt=(
            "你是检索助手。回答前必须用 kb_search 工具检索知识库获取依据，再基于检索结果回答。"
            f"知识库 ID 固定为：{kb_id}。"
        ),
        llm=llm, tools=[kb_search], max_steps=6,
    )
    r2 = await retriever.run("多智能体系统的核心挑战有哪些？请基于知识库回答。")
    print("【kb_search】输出:", r2.output)
    print("【kb_search】工具调用次数:", len(r2.tool_trace))
    for t in r2.tool_trace:
        print("  - 工具:", t["name"], "| 参数:", t.get("arguments"))


if __name__ == "__main__":
    asyncio.run(main())
