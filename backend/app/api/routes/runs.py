import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import get_agent_registry, get_run_manager, get_workflow_registry
from app.core.agent.registry import AgentRegistry
from app.workflow.registry import WorkflowRegistry
from app.workflow.runner import RunManager

router = APIRouter(prefix="/api/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    workflow_name: str = "research_report"
    input: dict = Field(default_factory=dict)


@router.post("")
async def create_run(body: CreateRunRequest,
                     run_manager: RunManager = Depends(get_run_manager),
                     agent_reg: AgentRegistry = Depends(get_agent_registry),
                     wf_reg: WorkflowRegistry = Depends(get_workflow_registry)):
    try:
        wf_reg.get(body.workflow_name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {body.workflow_name}")
    run_id = await run_manager.start(body.workflow_name, body.input, agent_reg, wf_reg)
    return {"run_id": run_id}


@router.get("")
def list_runs(run_manager: RunManager = Depends(get_run_manager)):
    return {"runs": run_manager.list_runs()}


@router.get("/{run_id}")
def get_run(run_id: str, run_manager: RunManager = Depends(get_run_manager)):
    run = run_manager.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"运行不存在: {run_id}")
    return {
        "run_id": run_id,
        "status": run["status"],
        "result": run["result"],
        "error": run["error"],
        "workflow_name": run.get("workflow_name"),
        "created_at": run.get("created_at"),
        "finished_at": run.get("finished_at"),
    }


@router.get("/{run_id}/events")
async def run_events(run_id: str, run_manager: RunManager = Depends(get_run_manager)):
    run = run_manager.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"运行不存在: {run_id}")

    async def gen():
        while True:
            event = await run["queue"].get()
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if event.get("type") in ("done", "error"):
                break

    return StreamingResponse(gen(), media_type="text/event-stream")
