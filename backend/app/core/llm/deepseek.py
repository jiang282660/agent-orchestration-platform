"""DeepSeek 客户端（OpenAI 兼容协议，支持 function-calling + 指数退避重试）。"""

import asyncio
import json
import time
from typing import Any

from app.core.llm.base import BaseLLM, LLMResponse, ToolCall

# 永久性错误（鉴权/参数），重试无意义，直接抛出
_NON_RETRYABLE = {400, 401, 403, 404, 422}


class DeepSeekLLM(BaseLLM):
    def __init__(self, settings):
        from openai import AsyncOpenAI  # 惰性导入，避免离线测试强依赖 openai

        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.deepseek_api_key or "EMPTY",
            base_url=settings.deepseek_base_url,
            timeout=settings.llm_timeout,
        )
        self._model = settings.deepseek_model

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self._settings.llm_temperature,
            "max_tokens": max_tokens or self._settings.llm_max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if response_format:
            kwargs["response_format"] = response_format

        resp = None
        latency = 0.0
        for attempt in range(self._settings.llm_max_retries + 1):
            t0 = time.perf_counter()
            try:
                resp = await self._client.chat.completions.create(**kwargs)
                latency = (time.perf_counter() - t0) * 1000
                break
            except Exception as e:
                status = getattr(e, "status_code", None) or getattr(e, "code", None)
                if status in _NON_RETRYABLE:
                    raise
                if attempt >= self._settings.llm_max_retries:
                    raise
                await asyncio.sleep(self._settings.llm_retry_backoff * (2 ** attempt))

        msg = resp.choices[0].message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        usage = {}
        if getattr(resp, "usage", None):
            u = resp.usage
            usage = {
                "prompt_tokens": getattr(u, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(u, "completion_tokens", 0) or 0,
                "total_tokens": getattr(u, "total_tokens", 0) or 0,
            }

        return LLMResponse(content=msg.content, tool_calls=tool_calls, raw=resp,
                           usage=usage, latency_ms=round(latency, 1))
