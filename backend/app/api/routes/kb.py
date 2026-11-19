from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import get_kb_service
from app.kb.service import KnowledgeBaseService

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])


class CreateKBRequest(BaseModel):
    name: str
    description: str = ""
    chunk_size: int = 500
    chunk_overlap: int = 50


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)


@router.post("")
def create_kb(body: CreateKBRequest, svc: KnowledgeBaseService = Depends(get_kb_service)):
    kb = svc.create_kb(body.name, body.description, body.chunk_size, body.chunk_overlap)
    return kb.to_dict()


@router.get("")
def list_kbs(svc: KnowledgeBaseService = Depends(get_kb_service)):
    return {"knowledge_bases": svc.list_kbs()}


@router.post("/{kb_id}/documents")
async def upload_document(kb_id: str, file: UploadFile = File(...),
                          svc: KnowledgeBaseService = Depends(get_kb_service)):
    content = await file.read()
    try:
        return svc.add_document(kb_id, file.filename or "document.txt", content)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"知识库不存在: {kb_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{kb_id}/documents")
def list_documents(kb_id: str, svc: KnowledgeBaseService = Depends(get_kb_service)):
    try:
        return {"documents": svc.list_documents(kb_id)}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"知识库不存在: {kb_id}")


@router.post("/{kb_id}/search")
def search(kb_id: str, body: SearchRequest, svc: KnowledgeBaseService = Depends(get_kb_service)):
    try:
        results = svc.search(kb_id, body.query, body.top_k)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"知识库不存在: {kb_id}")
    return {"results": [r.to_dict() for r in results]}
