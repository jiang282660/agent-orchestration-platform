"""LLM 网关抽象基类。"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

    def to_openai(self) -> dict:
        """转为 OpenAI messages 中 assistant 消息的 tool_calls 元素。"""
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": json.dumps(self.arguments, ensure_ascii=False)},
        }


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None
    usage: dict = field(default_factory=dict)   # prompt_tokens / completion_tokens / total_tokens
    latency_ms: float = 0.0


class BaseLLM(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """执行一次对话补全。messages 采用 OpenAI 格式。"""
        raise NotImplementedError
