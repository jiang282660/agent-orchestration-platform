from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_agent_registry, get_llm, get_tool_registry
from app.core.agent.base import Agent
from app.core.agent.registry import AgentRegistry
from app.core.tool import ToolRegistry

router = APIRouter(prefix="/api/agents", tags=["agents"])


class RegisterAgentRequest(BaseModel):
    id: str
    name: str
    role_prompt: str
    tool_names: list[str] = Field(default_factory=list)
    max_steps: int = 10
    temperature: float | None = None
    max_tokens: int | None = None


class RunAgentRequest(BaseModel):
    task: str
    context: dict | None = None


@router.get("")
def list_agents(reg: AgentRegistry = Depends(get_agent_registry)):
    return {"agents": reg.list()}


@router.post("")
def register_agent(
    body: RegisterAgentRequest,
    reg: AgentRegistry = Depends(get_agent_registry),
    tools: ToolRegistry = Depends(get_tool_registry),
):
    resolved = []
    for name in body.tool_names:
        try:
            resolved.append(tools.get(name))
        except KeyError:
            raise HTTPException(status_code=400, detail=f"unknown tool: {name}")

    agent = Agent(
        id=body.id,
        name=body.name,
        role_prompt=body.role_prompt,
        llm=get_llm(),
        tools=resolved,
        max_steps=body.max_steps,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    reg.register(agent)
    return {"id": agent.id, "name": agent.name}


@router.post("/{agent_id}/run")
async def run_agent(
    agent_id: str,
    body: RunAgentRequest,
    reg: AgentRegistry = Depends(get_agent_registry),
):
    try:
        agent = reg.get(agent_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"agent not found: {agent_id}")
    result = await agent.run(body.task, body.context)
    return result.to_dict()
