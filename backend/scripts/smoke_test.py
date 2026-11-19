"""离线冒烟测试：不依赖网络 / API key，用 MockLLM 验证 ReAct 工具循环。

运行：cd backend && python scripts/smoke_test.py
"""

import asyncio
import sys
from pathlib import Path

# Windows 控制台默认 GBK，统一按 UTF-8 输出避免中文/emoji 报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 让脚本能 import app.*（脚本位于 backend/scripts 下）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.agent.base import Agent
from app.core.llm.mock import MockLLM
from app.core.tool import Tool


def add(a: int, b: int) -> int:
    return a + b


async def main():
    calc = Tool(
        name="add",
        description="两个整数相加",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
        func=add,
    )

    # 脚本：第 1 次 LLM 调用返回 tool_call，第 2 次返回最终答案
    script = [
        {"tool_calls": [{"id": "call_1", "name": "add", "arguments": {"a": 3, "b": 5}}]},
        {"content": "结果是 8"},
    ]
    llm = MockLLM(script=script)
    agent = Agent(id="demo", name="demo", role_prompt="你是一个会用工具的助手。", llm=llm, tools=[calc])

    result = await agent.run("3 + 5 等于多少？")
    print("=== 冒烟测试结果 ===")
    print("输出:", result.output)
    print("步数:", result.steps)
    print("工具轨迹:", result.tool_trace)
    print("降级标记:", result.degraded)

    assert result.output == "结果是 8", "输出不符合预期"
    assert len(result.tool_trace) == 1, "应恰好有一次工具调用"
    assert result.tool_trace[0]["result"] == "8", "工具执行结果应为 8"
    assert not result.degraded
    print("✅ 冒烟测试通过：ReAct 工具循环正常")


if __name__ == "__main__":
    asyncio.run(main())
