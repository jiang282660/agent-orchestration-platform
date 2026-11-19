from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import (
    get_agent_registry,
    get_benchmark_service,
    get_workflow_registry,
)
from app.benchmark.service import BenchmarkService, compute_coverage
from app.core.agent.registry import AgentRegistry
from app.verification.rules import rule_check
from app.workflow.registry import WorkflowRegistry
from app.workflow.runner import run_workflow

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])


class CreateBenchmarkRequest(BaseModel):
    name: str
    description: str = ""
    workflow_name: str = "research_report"
    items: list[dict] = Field(default_factory=list)  # [{question, golden_points: [...]}]


class RunBenchmarkRequest(BaseModel):
    kb_id: str


@router.post("")
def create_benchmark(body: CreateBenchmarkRequest, svc: BenchmarkService = Depends(get_benchmark_service)):
    return svc.create_benchmark(body.name, body.description, body.workflow_name, body.items)


@router.get("")
def list_benchmarks(svc: BenchmarkService = Depends(get_benchmark_service)):
    return {"benchmarks": svc.list_benchmarks()}


@router.get("/{b_id}")
def get_benchmark(b_id: str, svc: BenchmarkService = Depends(get_benchmark_service)):
    try:
        return svc.get_benchmark(b_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"基准集不存在: {b_id}")


@router.post("/{b_id}/run")
async def run_benchmark(
    b_id: str,
    body: RunBenchmarkRequest,
    svc: BenchmarkService = Depends(get_benchmark_service),
    agent_reg: AgentRegistry = Depends(get_agent_registry),
    wf_reg: WorkflowRegistry = Depends(get_workflow_registry),
):
    try:
        bench = svc.get_benchmark(b_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"基准集不存在: {b_id}")

    results = []
    for item in bench["items"]:
        state, _ = await run_workflow(bench["workflow_name"],
                                      {"topic": item["question"], "kb_id": body.kb_id},
                                      agent_reg, wf_reg)
        draft = state.get("draft") or ""
        coverage, covered, missing = compute_coverage(draft, item["golden_points"])
        rule = rule_check(draft)
        svc.record_run(b_id, item["id"], coverage, {"covered": covered, "missing": missing})
        results.append({"question": item["question"], "coverage": coverage,
                        "covered": covered, "missing": missing, "rule_score": rule["score"]})

    avg = round(sum(r["coverage"] for r in results) / len(results), 3) if results else 0.0
    return {"avg_coverage": avg, "results": results}
