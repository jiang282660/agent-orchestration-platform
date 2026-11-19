"""内置示例工具：用于验证 ReAct 工具循环。M2 会在此基础上加 kb_search。"""

import ast
import operator
from datetime import datetime

from app.core.tool import Tool


# ---- 安全计算器：仅允许数字与四则/幂/取模/一元运算，避免 eval 注入 ----
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNOPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNOPS:
        return _UNOPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


def _safe_calc(expression: str):
    return _eval(ast.parse(expression, mode="eval"))


def _current_time():
    return datetime.now().isoformat(timespec="seconds")


calculator = Tool(
    name="calculator",
    description="计算一个数学表达式，支持 + - * / ** % 与括号，例如 '(3+5)*2'",
    parameters={
        "type": "object",
        "properties": {"expression": {"type": "string", "description": "数学表达式"}},
        "required": ["expression"],
    },
    func=_safe_calc,
)

get_current_time = Tool(
    name="get_current_time",
    description="获取当前日期时间",
    parameters={"type": "object", "properties": {}},
    func=_current_time,
)

BUILTIN_TOOLS = [calculator, get_current_time]
