"""kb_search 工具：让 Agent 能检索知识库。"""

from app.core.tool import Tool
from app.kb.service import KnowledgeBaseService


def make_kb_search_tool(service: KnowledgeBaseService) -> Tool:
    def _search(query: str, kb_id: str) -> list[dict]:
        results = service.search(kb_id, query, top_k=5)
        return [r.to_dict() for r in results]

    return Tool(
        name="kb_search",
        description="在指定知识库中检索相关内容，返回带来源的文本片段。kb_id 为知识库 ID，query 为检索查询。",
        parameters={
            "type": "object",
            "properties": {
                "kb_id": {"type": "string", "description": "知识库 ID"},
                "query": {"type": "string", "description": "检索查询语句"},
            },
            "required": ["kb_id", "query"],
        },
        func=_search,
    )
