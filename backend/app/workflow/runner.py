"""工作流运行器与运行管理器（异步执行 + SSE 事件流 + SQLite 持久化）。"""

import asyncio
import json
from datetime import datetime

from app.config import get_settings
from app.core.agent.registry import AgentRegistry
from app.core.state import RunState
from app.db import RunRow, RunStepRow, gen_id, get_db
from app.workflow.dsl import iter_nodes
from app.workflow.engine import WorkflowEngine
from app.workflow.registry import WorkflowRegistry

# 需要持久化为 run_steps 的事件类型
_PERSIST_EVENT_TYPES = ("agent", "rule", "expand", "loop")


async def run_workflow(name: str, input_dict: dict,
                       agent_registry: AgentRegistry,
                       workflow_registry: WorkflowRegistry,
                       event_queue: asyncio.Queue | None = None) -> tuple[RunState, list[dict]]:
    spec = workflow_registry.get(name)
    agents = {}
    for n in iter_nodes(spec):
        if n.agent and n.agent not in agents:
            agents[n.agent] = agent_registry.get(n.agent)
    engine = WorkflowEngine(agents, event_queue=event_queue,
                            max_concurrency=get_settings().max_concurrency)
    state = RunState(input_dict)
    await engine.run(spec, state)
    return state, engine.events


class RunManager:
    """运行管理器：异步启动工作流，事件经 asyncio.Queue 供 SSE 流式推送，运行轨迹落库可回溯。"""

    def __init__(self):
        self._runs: dict[str, dict] = {}

    async def start(self, workflow_name: str, input_dict: dict,
                    agent_registry: AgentRegistry,
                    workflow_registry: WorkflowRegistry) -> str:
        run_id = gen_id("run")
        queue: asyncio.Queue = asyncio.Queue()
        self._runs[run_id] = {"status": "running", "queue": queue, "result": None, "error": None}
        db = get_db()
        with db.session() as s:
            s.add(RunRow(id=run_id, workflow_name=workflow_name,
                         input_json=json.dumps(input_dict, ensure_ascii=False),
                         status="running", created_at=datetime.now().isoformat(timespec="seconds")))
            s.commit()
        asyncio.create_task(self._execute(run_id, workflow_name, input_dict,
                                          agent_registry, workflow_registry, queue))
        return run_id

    async def _execute(self, run_id: str, workflow_name: str, input_dict: dict,
                       agent_registry: AgentRegistry, workflow_registry: WorkflowRegistry,
                       queue: asyncio.Queue) -> None:
        db = get_db()
        try:
            state, events = await run_workflow(workflow_name, input_dict, agent_registry, workflow_registry,
                                               event_queue=queue)
            result = state.snapshot()
            self._runs[run_id]["result"] = result
            self._runs[run_id]["status"] = "done"
            with db.session() as s:
                row = s.get(RunRow, run_id)
                if row:
                    row.status = "done"
                    row.result_json = json.dumps(result, ensure_ascii=False)
                    row.finished_at = datetime.now().isoformat(timespec="seconds")
                self._persist_steps(s, run_id, events)
                s.commit()
            await queue.put({"type": "done", "final_state": result})
        except Exception as e:
            self._runs[run_id]["status"] = "error"
            self._runs[run_id]["error"] = str(e)
            with db.session() as s:
                row = s.get(RunRow, run_id)
                if row:
                    row.status = "error"
                    row.error = str(e)
                    row.finished_at = datetime.now().isoformat(timespec="seconds")
                s.commit()
            await queue.put({"type": "error", "message": str(e)})

    def _persist_steps(self, session, run_id: str, events: list[dict]) -> None:
        for ev in events:
            if ev.get("type") not in _PERSIST_EVENT_TYPES:
                continue
            output = ev.get("output") if ev.get("type") == "agent" else ev.get("result")
            tokens = ev.get("tokens") or {}
            session.add(RunStepRow(
                id=gen_id("step"),
                run_id=run_id,
                node_id=ev.get("node"),
                agent_id=ev.get("agent"),
                status="done",
                output_json=json.dumps(output, ensure_ascii=False, default=str)[:8000],
                tokens=tokens.get("total_tokens", 0) if isinstance(tokens, dict) else 0,
                latency_ms=ev.get("latency_ms") or 0.0,
                iteration=ev.get("iteration"),
                degraded=int(bool(ev.get("degraded"))),
                created_at=datetime.now().isoformat(timespec="seconds"),
            ))

    def get(self, run_id: str) -> dict | None:
        if run_id in self._runs:
            return self._runs[run_id]
        # 回退到持久化历史（重启后仍可查询）
        db = get_db()
        with db.session() as s:
            row = s.get(RunRow, run_id)
            if not row:
                return None
            result = json.loads(row.result_json) if row.result_json else None
            return {"status": row.status, "result": result, "error": row.error,
                    "workflow_name": row.workflow_name, "created_at": row.created_at,
                    "finished_at": row.finished_at}

    def list_runs(self, limit: int = 20) -> list[dict]:
        db = get_db()
        with db.session() as s:
            rows = s.query(RunRow).order_by(RunRow.created_at.desc()).limit(limit).all()
        return [{"run_id": r.id, "workflow_name": r.workflow_name, "status": r.status,
                 "created_at": r.created_at, "finished_at": r.finished_at} for r in rows]
