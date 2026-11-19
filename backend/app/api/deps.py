"""共享依赖：工具注册中心、Agent 注册中心、知识库服务、工作流注册中心、LLM 客户端。"""

from functools import lru_cache

from app.benchmark.service import BenchmarkService
from app.config import build_llm, get_settings
from app.core.agent.registry import AgentRegistry
from app.core.tool import ToolRegistry
from app.kb.service import KnowledgeBaseService
from app.tools.builtin import BUILTIN_TOOLS
from app.tools.kb_tool import make_kb_search_tool
from app.workflow.registry import WorkflowRegistry
from app.workflow.runner import RunManager


@lru_cache
def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()


@lru_cache
def get_tool_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register_many(BUILTIN_TOOLS)
    reg.register(make_kb_search_tool(get_kb_service()))
    return reg


@lru_cache
def get_agent_registry() -> AgentRegistry:
    return AgentRegistry()


@lru_cache
def get_workflow_registry() -> WorkflowRegistry:
    return WorkflowRegistry()


@lru_cache
def get_benchmark_service() -> BenchmarkService:
    return BenchmarkService()


@lru_cache
def get_run_manager() -> RunManager:
    return RunManager()


@lru_cache
def get_llm():
    return build_llm(get_settings())
