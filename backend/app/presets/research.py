"""预置「研究报告生成」团队与工作流（六角色：规划/检索/分析/撰写/审校/验证）。"""

from pathlib import Path

from pydantic import BaseModel

from app.core.agent.base import Agent
from app.core.agent.registry import AgentRegistry
from app.core.tool import ToolRegistry
from app.workflow.dsl import parse_workflow
from app.workflow.registry import WorkflowRegistry

_WORKFLOW_FILE = Path(__file__).parent / "research_workflow.yaml"


class PlannerOutput(BaseModel):
    outline: str
    subtasks: list[str]


class ReviewOutput(BaseModel):
    score: float          # 总体评分 0~1
    relevance: float      # 相关性
    accuracy: float       # 准确性
    completeness: float   # 完整性
    fluency: float        # 流畅性
    feedback: str         # 具体修改建议


class VerifyOutput(BaseModel):
    verification_score: float
    verified_claims: list[str]
    unsupported_claims: list[str]
    summary: str


def register_research_preset(
    agent_registry: AgentRegistry,
    tool_registry: ToolRegistry,
    workflow_registry: WorkflowRegistry,
    llm,
) -> None:
    kb_search = tool_registry.get("kb_search")

    agents = [
        Agent(
            id="planner", name="规划者",
            role_prompt="你是研究规划专家。根据用户给出的研究主题，制定清晰的研究大纲，并把主题拆解为 2~4 个可并行执行的子任务，每个子任务聚焦一个具体方面。",
            llm=llm, output_model=PlannerOutput, max_steps=6,
        ),
        Agent(
            id="retriever", name="检索者",
            role_prompt="你是资料检索专家。使用 kb_search 工具在知识库中检索与给定子任务相关的资料，整理出带来源的关键片段。",
            llm=llm, tools=[kb_search], max_steps=8,
        ),
        Agent(
            id="analyzer", name="分析者",
            role_prompt="你是分析专家。基于提供的检索资料，分析并提炼与子任务相关的关键论点、支撑证据与结论，并在每条论点后保留对应的来源标注。",
            llm=llm, max_steps=6,
        ),
        Agent(
            id="writer", name="撰写者",
            role_prompt="你是报告撰写专家。根据研究大纲和各子任务的分析结果，撰写结构完整、逻辑清晰的研究报告。每个关键论点后必须用【来源：文档名】标注出处。若收到审校反馈，需针对反馈逐条修改完善，并确保每个论点都有来源标注。",
            llm=llm, max_steps=10,
        ),
        Agent(
            id="reviewer", name="审校者",
            role_prompt=(
                "你是报告审校专家。对报告草稿进行严格审校，从相关性、准确性、完整性、流畅性四个维度打分（0~1），"
                "检查关键论点是否有【来源】标注，并给出具体、可执行的修改建议。\n"
                "评分锚点（务必按此校准，避免分数无依据跳动）：0.60=基本可用但信息不足或缺少来源；"
                "0.80=达到可交付标准（论据较充分、关键论点有来源标注）；"
                "0.90=优秀（结构完整、论据翔实、几乎无需修改）。"
            ),
            llm=llm, output_model=ReviewOutput, max_steps=8,
        ),
        Agent(
            id="verifier", name="验证者",
            role_prompt="你是事实核查专家。使用 kb_search 工具检索知识库，逐条核查报告中的关键断言是否有证据支撑，区分「有据断言」与「无据断言」，并给出核查通过率。",
            llm=llm, tools=[kb_search], output_model=VerifyOutput, max_steps=10,
        ),
    ]
    for a in agents:
        agent_registry.register(a)

    workflow_registry.register(parse_workflow(_WORKFLOW_FILE))
