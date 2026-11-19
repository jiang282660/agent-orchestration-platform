"""工作流 DSL：定义、解析（YAML/JSON/dict）与校验（依赖存在性 + 环检测）。"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class NodeSpec(BaseModel):
    id: str
    type: str = "agent"  # agent | expand | loop | rule
    agent: str | None = None  # agent 类型节点必填
    task: str | None = None   # 指令模板，支持 {key} 占位符
    reads: list[str] = Field(default_factory=list)
    writes: dict[str, str] = Field(default_factory=dict)  # state_key -> output_field（"*" 表示整体输出）
    depends_on: list[str] = Field(default_factory=list)
    # expand 专用
    input_key: str | None = None   # 读取的列表字段
    item_key: str = "item"         # 注入子图时每个子项使用的键
    output_node: str | None = None # 子图中要收集输出的节点 id
    output_key: str | None = None  # 收集结果的列表写入的 state 键
    subgraph: WorkflowSpec | None = None
    # loop 专用
    body: WorkflowSpec | None = None   # 循环体（子工作流）
    score_key: str | None = None       # 每轮读取的评分字段
    threshold: float | None = None     # 达标阈值（score >= threshold 则退出）
    max_iterations: int | None = None  # 最大轮次


class WorkflowSpec(BaseModel):
    name: str
    nodes: list[NodeSpec]
    team_id: str | None = None


NodeSpec.model_rebuild()


def parse_workflow(source) -> WorkflowSpec:
    if isinstance(source, WorkflowSpec):
        spec = source
    else:
        data = _to_dict(source)
        spec = WorkflowSpec.model_validate(data)
    validate_dag(spec)
    return spec


def _to_dict(source) -> dict:
    if isinstance(source, dict):
        return source
    if isinstance(source, (str, Path)):
        p = Path(source)
        if p.exists():
            text = p.read_text(encoding="utf-8")
        else:
            text = str(source)
        return _parse_text(text)
    raise ValueError("工作流定义需为 dict、文件路径或 YAML/JSON 字符串")


def _parse_text(text: str) -> dict:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    try:
        import yaml
        return yaml.safe_load(text)
    except ImportError:
        raise ValueError("YAML 格式需要安装 pyyaml，或改用 JSON 格式")


def iter_nodes(spec: WorkflowSpec):
    """递归遍历所有节点（含 expand 子图与 loop 循环体）。"""
    for n in spec.nodes:
        yield n
        if n.type == "expand" and n.subgraph:
            yield from iter_nodes(n.subgraph)
        if n.type == "loop" and n.body:
            yield from iter_nodes(n.body)


def validate_dag(spec: WorkflowSpec) -> None:
    ids = {n.id for n in spec.nodes}
    for n in spec.nodes:
        if n.type == "agent" and not n.agent:
            raise ValueError(f"节点 {n.id} 是 agent 类型但未指定 agent")
        for d in n.depends_on:
            if d not in ids:
                raise ValueError(f"节点 {n.id} 依赖不存在的节点 {d}")
        if n.type == "expand":
            if not n.subgraph or not n.input_key or not n.output_node or not n.output_key:
                raise ValueError(f"expand 节点 {n.id} 需配置 subgraph/input_key/output_node/output_key")
            validate_dag(n.subgraph)
        if n.type == "loop":
            if not n.body or not n.score_key or n.threshold is None or not n.max_iterations:
                raise ValueError(f"loop 节点 {n.id} 需配置 body/score_key/threshold/max_iterations")
            validate_dag(n.body)
        if n.type == "rule" and not n.input_key:
            raise ValueError(f"rule 节点 {n.id} 需配置 input_key（待核查的 state 字段）")
    _detect_cycle(spec)


def _detect_cycle(spec: WorkflowSpec) -> None:
    adj = {n.id: n.depends_on for n in spec.nodes}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n.id: WHITE for n in spec.nodes}

    def dfs(u):
        color[u] = GRAY
        for v in adj[u]:
            if color[v] == GRAY:
                raise ValueError(f"工作流存在环：{u} -> {v}")
            if color[v] == WHITE:
                dfs(v)
        color[u] = BLACK

    for n in spec.nodes:
        if color[n.id] == WHITE:
            dfs(n.id)
