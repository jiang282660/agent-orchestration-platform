"""知识库离线冒烟测试：验证解析 → 分块 → BM25 检索链路（不依赖网络）。

运行：cd backend && python scripts/kb_smoke_test.py
"""

import os
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 用临时 DB 避免污染真实数据
os.environ["DB_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

from app.kb.service import KnowledgeBaseService  # noqa: E402


def main():
    svc = KnowledgeBaseService()
    kb = svc.create_kb("测试知识库", "演示用")

    text = (
        "多智能体系统是指由多个自主智能体组成的系统。\n"
        "每个智能体能够感知环境、做出决策并执行动作。\n"
        "多智能体系统常用于复杂任务分解与协作。\n"
        "工作流编排是协调多个智能体协作的关键技术。\n"
    )
    result = svc.add_document(kb.id, "test.txt", text.encode("utf-8"))
    print("文档入库:", result)

    results = svc.search(kb.id, "什么是多智能体系统", top_k=3)
    print("检索命中:", len(results))
    for r in results:
        print(f"  - score={r.score} | {r.text[:40]}")

    assert result["chunks_count"] >= 1, "应至少分出一个 chunk"
    assert len(results) >= 1, "应至少检索到一个结果"
    assert any("多智能体" in r.text for r in results), "检索结果应命中相关片段"
    print("✅ 知识库冒烟测试通过：解析 → 分块 → BM25 检索正常")


if __name__ == "__main__":
    main()
