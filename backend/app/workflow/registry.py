"""工作流注册中心。"""

from app.workflow.dsl import WorkflowSpec


class WorkflowRegistry:
    def __init__(self):
        self._workflows: dict[str, WorkflowSpec] = {}

    def register(self, spec: WorkflowSpec) -> None:
        self._workflows[spec.name] = spec

    def get(self, name: str) -> WorkflowSpec:
        if name not in self._workflows:
            raise KeyError(f"工作流不存在: {name}")
        return self._workflows[name]

    def all(self) -> list[dict]:
        return [{"name": s.name, "nodes": [n.id for n in s.nodes]} for s in self._workflows.values()]

    def describe(self, name: str) -> dict:
        """返回工作流完整结构（含依赖边与子图/循环体），供前端 DAG 可视化。"""
        spec = self.get(name)
        return {"name": spec.name, "nodes": [self._node_desc(n) for n in spec.nodes]}

    @staticmethod
    def _node_desc(n) -> dict:
        d = {"id": n.id, "type": n.type, "depends_on": n.depends_on, "agent": n.agent}
        if n.type == "expand" and n.subgraph:
            d["subgraph"] = [{"id": x.id, "type": x.type, "depends_on": x.depends_on, "agent": x.agent}
                             for x in n.subgraph.nodes]
        if n.type == "loop" and n.body:
            d["body"] = [{"id": x.id, "type": x.type, "depends_on": x.depends_on, "agent": x.agent}
                         for x in n.body.nodes]
        return d
