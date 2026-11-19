from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_agent_registry, get_workflow_registry
from app.core.agent.registry import AgentRegistry
from app.core.state import RunState
from app.workflow.dsl import iter_nodes, parse_workflow
from app.workflow.engine import WorkflowEngine
from app.workflow.registry import WorkflowRegistry

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class RegisterWorkflowRequest(BaseModel):
    definition: dict


class RunWorkflowRequest(BaseModel):
    input: dict = Field(default_factory=dict)


@router.post("")
def register_workflow(body: RegisterWorkflowRequest, wf_reg: WorkflowRegistry = Depends(get_workflow_registry)):
    spec = parse_workflow(body.definition)
    wf_reg.register(spec)
    return {"name": spec.name, "nodes": [n.id for n in spec.nodes]}


@router.get("")
def list_workflows(wf_reg: WorkflowRegistry = Depends(get_workflow_registry)):
    return {"workflows": wf_reg.all()}


@router.get("/{name}")
def get_workflow(name: str, wf_reg: WorkflowRegistry = Depends(get_workflow_registry)):
    try:
        return wf_reg.describe(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {name}")


@router.post("/{name}/run")
async def run_workflow(name: str, body: RunWorkflowRequest,
                       wf_reg: WorkflowRegistry = Depends(get_workflow_registry),
                       agent_reg: AgentRegistry = Depends(get_agent_registry)):
    try:
        spec = wf_reg.get(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {name}")

    agents = {}
    for n in iter_nodes(spec):
        if n.agent and n.agent not in agents:
            try:
                agents[n.agent] = agent_reg.get(n.agent)
            except KeyError:
                raise HTTPException(status_code=400, detail=f"工作流引用了未注册的 Agent: {n.agent}")

    engine = WorkflowEngine(agents)
    state = RunState(body.input)
    await engine.run(spec, state)
    return {"final_state": state.snapshot(), "events": engine.events}
