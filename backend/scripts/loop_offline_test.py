"""Self-Loop 循环控制器离线测试：验证评分达标即退出、未达标继续、轮次上限（不依赖网络）。

运行：cd backend && python scripts/loop_offline_test.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DB_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

from pydantic import BaseModel  # noqa: E402
from app.core.agent.base import Agent  # noqa: E402
from app.core.llm.mock import MockLLM  # noqa: E402
from app.core.state import RunState  # noqa: E402
from app.workflow.dsl import parse_workflow  # noqa: E402
from app.workflow.engine import WorkflowEngine  # noqa: E402


class Review(BaseModel):
    score: float
    feedback: str


async def main():
    writer = Agent("writer", "撰写", "写草稿",
                   MockLLM([{"content": "草稿1"}, {"content": "草稿2"}, {"content": "草稿3"}]))
    reviewer = Agent("reviewer", "审校", "打分",
                     MockLLM([
                         {"content": '{"score": 0.5, "feedback": "不够完整"}'},
                         {"content": '{"score": 0.85, "feedback": "通过"}'},
                         {"content": '{"score": 0.9, "feedback": "优秀"}'},
                     ]),
                     output_model=Review)

    spec = parse_workflow({
        "name": "loop_test",
        "nodes": [
            {"id": "quality_loop", "type": "loop",
             "score_key": "review_score", "threshold": 0.8, "max_iterations": 3,
             "body": {"name": "body", "nodes": [
                 {"id": "writer", "agent": "writer", "task": "写草稿", "writes": {"draft": "*"}},
                 {"id": "reviewer", "agent": "reviewer", "depends_on": ["writer"],
                  "task": "审校 {draft}", "reads": ["draft"],
                  "writes": {"review_score": "score", "feedback": "feedback"}},
             ]}},
        ],
    })

    engine = WorkflowEngine({"writer": writer, "reviewer": reviewer})
    state = RunState({})
    await engine.run(spec, state)

    print("最终 draft:", state.get("draft"))
    print("最终 review_score:", state.get("review_score"))
    print("评分曲线:", state.get("quality_loop_score_curve"))
    loop_events = [e for e in engine.events if e.get("type") == "loop"]
    print("loop 事件:", loop_events)

    assert state.get("draft") == "草稿2", "第 2 轮达标后应停止，不应再写第 3 稿"
    assert state.get("review_score") == 0.85
    assert state.get("quality_loop_score_curve") == [0.5, 0.85]
    assert loop_events[0]["iterations"] == 2
    print("✅ Self-Loop 离线测试通过：未达标继续、达标退出、轮次记录正确")


if __name__ == "__main__":
    asyncio.run(main())
