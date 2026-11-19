from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import (
    get_agent_registry,
    get_llm,
    get_tool_registry,
    get_workflow_registry,
)
from app.api.routes import agents, benchmarks, health, kb, runs, workflows
from app.config import get_settings
from app.presets.research import register_research_preset


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 演示期放开，生产需收紧
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(agents.router)
    app.include_router(kb.router)
    app.include_router(workflows.router)
    app.include_router(benchmarks.router)
    app.include_router(runs.router)

    # 注册预置「研究报告生成」团队与工作流
    register_research_preset(
        get_agent_registry(), get_tool_registry(), get_workflow_registry(), get_llm()
    )
    return app


app = create_app()
