"""Agent 基类：ReAct 多步工具循环 + 结构化输出可靠性。"""

import json
from dataclasses import dataclass, field
from typing import Any

from app.core.llm.base import BaseLLM
from app.core.tool import Tool


@dataclass
class AgentResult:
    agent_id: str
    output: Any = None
    steps: int = 0
    tool_trace: list[dict] = field(default_factory=list)
    degraded: bool = False
    error: str | None = None
    tokens: dict = field(default_factory=dict)   # prompt_tokens / completion_tokens / total_tokens
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "output": self.output,
            "steps": self.steps,
            "tool_trace": self.tool_trace,
            "degraded": self.degraded,
            "error": self.error,
            "tokens": self.tokens,
            "latency_ms": self.latency_ms,
        }


class Agent:
    """Agent：在 max_steps 内反复调用 LLM，直到产出最终答案。

    循环逻辑：
      1. LLM 返回 tool_calls → 逐个执行工具，结果以 tool 消息回填，继续循环；
      2. LLM 返回最终文本 → 若设了 output_model 则做结构化校验，
         解析失败带错误反馈重试（≤2 次），仍失败则降级返回原文。
    """

    def __init__(
        self,
        id: str,
        name: str,
        role_prompt: str,
        llm: BaseLLM,
        tools: list[Tool] | None = None,
        max_steps: int = 10,
        temperature: float | None = None,
        max_tokens: int | None = None,
        output_model=None,  # 可选 Pydantic 模型，用于结构化输出校验
    ):
        self.id = id
        self.name = name
        self.role_prompt = role_prompt
        self.llm = llm
        self.tools = list(tools or [])
        self.max_steps = max_steps
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.output_model = output_model

    def _tool_schemas(self) -> list[dict]:
        return [t.to_openai() for t in self.tools]

    def _build_messages(self, task: str, context: dict | None) -> list[dict]:
        messages = [{"role": "system", "content": self.role_prompt}]
        if self.output_model is not None:
            schema = json.dumps(self.output_model.model_json_schema(), ensure_ascii=False)
            messages.append({
                "role": "system",
                "content": f"你必须输出 JSON，且严格符合以下 JSON Schema：\n{schema}",
            })
        if context:
            messages.append({"role": "system", "content": f"上下文数据：{json.dumps(context, ensure_ascii=False)}"})
        messages.append({"role": "user", "content": task})
        return messages

    def _try_parse(self, content: str):
        if self.output_model is None:
            return content
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None
        try:
            return self.output_model.model_validate(data).model_dump()
        except Exception:
            return None

    def _parse_error_hint(self) -> str:
        schema = json.dumps(self.output_model.model_json_schema(), ensure_ascii=False)
        return f"你上一次的输出不是合法 JSON，无法通过校验。请重新输出，严格符合以下 JSON Schema：\n{schema}"

    async def _execute_tool(self, tool_call, tool_trace: list[dict]) -> str:
        tool = next((t for t in self.tools if t.name == tool_call.name), None)
        if tool is None:
            err = f"unknown tool: {tool_call.name}"
            tool_trace.append({"name": tool_call.name, "arguments": tool_call.arguments, "error": err})
            return err
        try:
            result = await tool.run(tool_call.arguments)
        except Exception as e:  # 工具异常不中断循环，作为结果回传让 LLM 自行处理
            result = f"tool execution error: {e}"
        tool_trace.append({"name": tool_call.name, "arguments": tool_call.arguments, "result": result})
        return result

    async def run(self, task: str, context: dict | None = None) -> AgentResult:
        messages = self._build_messages(task, context)
        tool_trace: list[dict] = []
        parse_retries = 0
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        total_latency = 0.0

        def _usage_add(u: dict) -> None:
            for k in total_usage:
                total_usage[k] += u.get(k, 0) or 0

        for step in range(1, self.max_steps + 1):
            resp = await self.llm.chat(
                messages,
                tools=self._tool_schemas(),
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            total_latency += resp.latency_ms or 0.0
            _usage_add(resp.usage or {})

            if resp.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": resp.content or "",
                    "tool_calls": [tc.to_openai() for tc in resp.tool_calls],
                })
                for tc in resp.tool_calls:
                    result = await self._execute_tool(tc, tool_trace)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": result})
                continue

            content = resp.content or ""
            parsed = self._try_parse(content)
            if parsed is not None:
                return AgentResult(agent_id=self.id, output=parsed, steps=step, tool_trace=tool_trace,
                                   tokens=dict(total_usage), latency_ms=round(total_latency, 1))

            # 结构化输出解析失败 → 带错误反馈重试（≤2 次）
            if self.output_model is not None and parse_retries < 2:
                parse_retries += 1
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": self._parse_error_hint()})
                continue

            return AgentResult(
                agent_id=self.id,
                output=content,
                steps=step,
                tool_trace=tool_trace,
                degraded=self.output_model is not None,
                error="output parse failed" if self.output_model is not None else None,
                tokens=dict(total_usage),
                latency_ms=round(total_latency, 1),
            )

        return AgentResult(agent_id=self.id, steps=self.max_steps, tool_trace=tool_trace,
                           degraded=True, error="max_steps exceeded",
                           tokens=dict(total_usage), latency_ms=round(total_latency, 1))
