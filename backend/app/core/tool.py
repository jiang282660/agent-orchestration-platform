"""Tool 定义与工具注册中心。"""

import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    """一个可被 Agent 调用的工具。

    parameters 为 JSON Schema 形式的参数定义，func 为实际执行函数（支持同步/异步）。
    """

    name: str
    description: str
    parameters: dict
    func: Callable[..., Any]

    def to_openai(self) -> dict:
        """转为 OpenAI function-calling 的 tools 元素。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def run(self, arguments: dict) -> str:
        """执行工具并返回字符串结果。"""
        result = self.func(**arguments)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, default=str)


class ToolRegistry:
    """工具注册中心：统一注册、查找、执行工具。"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def register_many(self, tools: list[Tool]) -> None:
        for t in tools:
            self.register(t)

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    async def execute(self, name: str, arguments: dict) -> str:
        return await self.get(name).run(arguments)
