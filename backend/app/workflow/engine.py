"""工作流引擎：DAG 就绪调度 + RunState 绑定 + expand 动态扇出 + loop 循环 + 事件流。"""

import asyncio
import json
import re
from typing import Any

from app.core.agent.base import Agent
from app.core.state import RunState
from app.verification.rules import rule_check
from app.workflow.dsl import NodeSpec, WorkflowSpec

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class WorkflowEngine:
    def __init__(self, agents: dict[str, Agent], event_queue: asyncio.Queue | None = None,
                 max_concurrency: int = 4):
        self.agents = agents
        self.events: list[dict] = []  # 执行轨迹（全量）
        self._queue = event_queue    # 可选：实时事件队列（SSE）
        self._sem = asyncio.Semaphore(max_concurrency)  # 动态扇出并发上限（限流保护）

    def _emit(self, event: dict) -> None:
        self.events.append(event)
        if self._queue is not None:
            self._queue.put_nowait(event)

    async def run(self, spec: WorkflowSpec, state: RunState) -> RunState:
        memo: dict[str, Any] = {}
        locks: dict[str, asyncio.Lock] = {}
        await asyncio.gather(*[self._run_node(n, spec, state, None, memo, locks) for n in spec.nodes])
        return state

    # ---- 递归 DAG 执行：节点先等待依赖（并行），再执行自身 ----
    # 每个节点一把锁 + 双重检查，避免同一节点被多个依赖并发触发时重复执行
    async def _run_node(self, node: NodeSpec, spec: WorkflowSpec, state: RunState,
                        inject: dict | None, memo: dict, locks: dict) -> Any:
        if node.id in memo:
            return memo[node.id]
        lock = locks.setdefault(node.id, asyncio.Lock())
        async with lock:
            if node.id in memo:
                return memo[node.id]
            deps = [n for n in spec.nodes if n.id in node.depends_on]
            if deps:
                await asyncio.gather(*[self._run_node(d, spec, state, inject, memo, locks) for d in deps])
            output = await self._execute_node(node, state, inject)
            memo[node.id] = output
            return output

    async def _execute_node(self, node: NodeSpec, state: RunState, inject: dict | None) -> Any:
        if node.type == "expand":
            return await self._execute_expand(node, state, inject)
        if node.type == "loop":
            return await self._execute_loop(node, state, inject)
        if node.type == "rule":
            return await self._execute_rule(node, state, inject)
        return await self._execute_agent(node, state, inject)

    # ---- 统一写回 state：writes 的 field 为 "*" 时写整体输出，否则取输出字典中的字段 ----
    def _apply_writes(self, node: NodeSpec, state: RunState, output: Any) -> None:
        for state_key, field in node.writes.items():
            if isinstance(output, dict) and field != "*":
                state.set(state_key, output.get(field))
            else:
                state.set(state_key, output)

    # ---- agent 节点 ----
    async def _execute_agent(self, node: NodeSpec, state: RunState, inject: dict | None) -> Any:
        agent = self.agents[node.agent]
        self._emit({"type": "start", "node": node.id, "agent": node.agent})
        context = self._build_context(node, state, inject)
        task = self._render(node.task or "", context)
        async with self._sem:  # 并发上限：限制同时进行的 LLM 调用
            result = await agent.run(task, context)
        output = result.output
        self._apply_writes(node, state, output)

        self._emit({
            "type": "agent", "node": node.id, "agent": node.agent, "output": output,
            "steps": result.steps, "tool_trace": result.tool_trace, "degraded": result.degraded,
            "tokens": result.tokens, "latency_ms": result.latency_ms,
        })
        return output

    # ---- rule 节点：确定性规则核查（不依赖 LLM）----
    async def _execute_rule(self, node: NodeSpec, state: RunState, inject: dict | None) -> Any:
        self._emit({"type": "start", "node": node.id, "agent": None})
        text = state.get(node.input_key) or ""
        result = rule_check(text)
        self._apply_writes(node, state, result)
        self._emit({"type": "rule", "node": node.id, "result": result})
        return result

    # ---- expand 节点：动态扇出，子图按子项并行执行 ----
    async def _execute_expand(self, node: NodeSpec, state: RunState, inject: dict | None) -> Any:
        self._emit({"type": "start", "node": node.id, "agent": None})
        items = state.get(node.input_key) or []
        if isinstance(items, str) or not isinstance(items, (list, tuple)):
            items = [items]
        items = list(items)

        async def run_item(item):
            sub_state = RunState(state.snapshot())  # 子状态继承共享 state
            sub_inject = {**(inject or {}), node.item_key: item}
            memo: dict[str, Any] = {}
            locks: dict[str, asyncio.Lock] = {}
            sub_nodes = node.subgraph.nodes
            await asyncio.gather(*[self._run_node(n, node.subgraph, sub_state, sub_inject, memo, locks)
                                   for n in sub_nodes])
            return memo.get(node.output_node)

        outputs = await asyncio.gather(*[run_item(i) for i in items])
        state.set(node.output_key, outputs)
        self._emit({"type": "expand", "node": node.id, "items": len(items), "outputs": outputs})
        return outputs

    # ---- loop 节点：Self-Loop「执行→评估→反馈→重执行」，评分达标或达轮次上限退出 ----
    async def _execute_loop(self, node: NodeSpec, state: RunState, inject: dict | None) -> Any:
        self._emit({"type": "start", "node": node.id, "agent": None})
        score_curve = []
        iterations = 0
        for iteration in range(1, node.max_iterations + 1):
            iterations = iteration
            memo: dict[str, Any] = {}
            locks: dict[str, asyncio.Lock] = {}
            await asyncio.gather(*[self._run_node(n, node.body, state, inject, memo, locks)
                                   for n in node.body.nodes])
            score = state.get(node.score_key)
            score_curve.append(score)
            self._emit({"type": "loop_iteration", "node": node.id, "iteration": iteration, "score": score})
            try:
                score_val = float(score) if score is not None else None
            except (TypeError, ValueError):
                score_val = None  # 评分无法解析时视为未达标，继续轮次（受 max_iterations 限制）
            if score_val is not None and score_val >= node.threshold:
                break
        state.set(node.id + "_score_curve", score_curve)
        self._emit({"type": "loop", "node": node.id, "iterations": iterations, "score_curve": score_curve})
        return score_curve

    # ---- 工具方法 ----
    def _build_context(self, node: NodeSpec, state: RunState, inject: dict | None) -> dict:
        ctx = {}
        snapshot = state.snapshot()
        for k in node.reads:
            if inject and k in inject:
                ctx[k] = inject[k]
            elif k in snapshot:
                ctx[k] = snapshot[k]
            else:
                ctx[k] = None
        return ctx

    def _render(self, template: str, context: dict) -> str:
        def repl(m):
            v = context.get(m.group(1), m.group(0))
            if v is None:
                return ""
            return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        return _PLACEHOLDER.sub(repl, template)
