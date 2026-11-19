"""确定性 Mock LLM：离线测试 ReAct 循环，不依赖网络 / API key。"""

from app.core.llm.base import BaseLLM, LLMResponse, ToolCall


class MockLLM(BaseLLM):
    """按脚本顺序回放响应。

    脚本每一项是 dict，二选一：
      {"content": "最终文本"}
      {"tool_calls": [{"id": "...", "name": "...", "arguments": {...}}]}
    脚本耗尽后返回空 content。
    """

    def __init__(self, script: list[dict] | None = None):
        self._script = list(script) if script else []
        self.calls = 0

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        self.calls += 1
        if self.calls <= len(self._script):
            item = self._script[self.calls - 1]
        else:
            item = {"content": ""}

        tool_calls = []
        for tc in item.get("tool_calls", []):
            tool_calls.append(ToolCall(id=tc["id"], name=tc["name"], arguments=tc.get("arguments", {})))
        return LLMResponse(content=item.get("content"), tool_calls=tool_calls)
