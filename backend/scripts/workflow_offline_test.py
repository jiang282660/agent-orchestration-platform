"""工作流引擎离线测试：验证 DAG 顺序、expand 动态扇出、RunState 读写（不依赖网络）。

运行：cd backend && python scripts/workflow_offline_test.py
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


class PlanOut(BaseModel):
    subtasks: list[str]


async def main():
    planner = Agent("planner", "规划", "拆解任务",
                    MockLLM([{"content": '{"subtasks": ["A", "B", "C"]}'}]), output_model=PlanOut)
    worker = Agent("worker", "工人", "处理子任务",
                   MockLLM([{"content": "OK1"}, {"content": "OK2"}, {"content": "OK3"}]))
    final = Agent("final", "汇总", "汇总结果", MockLLM([{"content": "汇总完成"}]))

    spec = parse_workflow({
        "name": "offline_test",
        "nodes": [
            {"id": "planner", "agent": "planner", "task": "拆解任务", "writes": {"subtasks": "subtasks"}},
            {"id": "fanout", "type": "expand", "depends_on": ["planner"],
             "input_key": "subtasks", "item_key": "subtask", "output_node": "worker", "output_key": "results",
             "subgraph": {"name": "sub", "nodes": [
                 {"id": "worker", "agent": "worker", "task": "处理 {subtask}", "reads": ["subtask"],
                  "writes": {"result": "*"}},
             ]}},
            {"id": "final", "agent": "final", "depends_on": ["fanout"], "task": "汇总 {results}",
             "reads": ["results"], "writes": {"summary": "*"}},
        ],
    })

    engine = WorkflowEngine({"planner": planner, "worker": worker, "final": final})
    state = RunState({})
    await engine.run(spec, state)

    print("最终 state:", state.snapshot())
    print("事件:", [(e["node"], e.get("type", "agent")) for e in engine.events])

    assert state.get("subtasks") == ["A", "B", "C"]
    assert len(state.get("results")) == 3
    assert state.get("summary") == "汇总完成"
    expand_events = [e for e in engine.events if e.get("type") == "expand"]
    assert len(expand_events) == 1 and expand_events[0]["items"] == 3
    print("✅ 工作流引擎离线测试通过：DAG 顺序 + expand 动态扇出 + RunState 读写正常")


if __name__ == "__main__":
    asyncio.run(main())
