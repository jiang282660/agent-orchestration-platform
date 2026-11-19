"""Agent 注册中心。"""

from app.core.agent.base import Agent


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> Agent:
        if agent_id not in self._agents:
            raise KeyError(f"Agent not found: {agent_id}")
        return self._agents[agent_id]

    def all(self) -> list[Agent]:
        return list(self._agents.values())

    def list(self) -> list[dict]:
        return [
            {"id": a.id, "name": a.name, "tools": [t.name for t in a.tools], "max_steps": a.max_steps}
            for a in self._agents.values()
        ]
