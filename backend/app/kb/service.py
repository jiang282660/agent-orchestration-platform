"""知识库服务：创建 KB、上传文档、解析分块、索引、检索。"""

import json
from datetime import datetime
from typing import Callable

from app.config import get_settings
from app.db import ChunkRow, DocumentRow, KnowledgeBaseRow, gen_id, get_db
from app.kb.chunker import Chunk, chunk_text
from app.kb.parser import parse_document
from app.kb.retriever import BaseRetriever, SearchResult, build_retriever


class KnowledgeBase:
    def __init__(self, id: str, name: str, description: str,
                 chunk_size: int, chunk_overlap: int, retriever: BaseRetriever,
                 retriever_type: str = "bm25"):
        self.id = id
        self.name = name
        self.description = description
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.retriever = retriever
        self.retriever_type = retriever_type

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "description": self.description,
                "chunk_size": self.chunk_size, "chunk_overlap": self.chunk_overlap,
                "retriever_type": self.retriever_type,
                "semantic_retrieval": self.retriever.semantic_available()}


class KnowledgeBaseService:
    def __init__(self, retriever_factory: Callable[[], BaseRetriever] | None = None,
                 retriever_type: str | None = None, embedding_model: str | None = None):
        settings = get_settings()
        self.retriever_type = retriever_type or settings.retriever_type
        self.embedding_model = embedding_model or settings.embedding_model
        self._retriever_factory = retriever_factory or (
            lambda: build_retriever(self.retriever_type, self.embedding_model)
        )
        self._kbs: dict[str, KnowledgeBase] = {}
        self.restore()

    # ---- 生命周期 ----
    def restore(self) -> None:
        """启动时从 DB 恢复所有知识库并重建检索索引。"""
        db = get_db()
        with db.session() as s:
            rows = s.query(KnowledgeBaseRow).all()
        for r in rows:
            kb = KnowledgeBase(r.id, r.name, r.description, r.chunk_size, r.chunk_overlap,
                               self._retriever_factory(), self.retriever_type)
            kb.retriever.index(self._load_chunks(r.id))
            self._kbs[r.id] = kb

    # ---- 知识库 CRUD ----
    def create_kb(self, name: str, description: str = "",
                  chunk_size: int = 500, chunk_overlap: int = 50) -> KnowledgeBase:
        kb_id = gen_id("kb")
        db = get_db()
        with db.session() as s:
            s.add(KnowledgeBaseRow(id=kb_id, name=name, description=description,
                                   chunk_size=chunk_size, chunk_overlap=chunk_overlap,
                                   created_at=datetime.now().isoformat(timespec="seconds")))
            s.commit()
        kb = KnowledgeBase(kb_id, name, description, chunk_size, chunk_overlap,
                           self._retriever_factory(), self.retriever_type)
        self._kbs[kb_id] = kb
        return kb

    def get_kb(self, kb_id: str) -> KnowledgeBase:
        if kb_id not in self._kbs:
            raise KeyError(f"知识库不存在: {kb_id}")
        return self._kbs[kb_id]

    def list_kbs(self) -> list[dict]:
        return [kb.to_dict() for kb in self._kbs.values()]

    # ---- 文档 ----
    def add_document(self, kb_id: str, filename: str, content: bytes) -> dict:
        kb = self.get_kb(kb_id)
        text = parse_document(filename, content)
        raw_chunks = chunk_text(text, kb.chunk_size, kb.chunk_overlap)

        doc_id = gen_id("doc")
        db = get_db()
        with db.session() as s:
            s.add(DocumentRow(id=doc_id, kb_id=kb_id, filename=filename, status="done",
                              chunks_count=len(raw_chunks),
                              created_at=datetime.now().isoformat(timespec="seconds")))
            for i, rc in enumerate(raw_chunks):
                cid = gen_id("chunk")
                meta = {"source": filename, "doc_id": doc_id}
                s.add(ChunkRow(id=cid, doc_id=doc_id, kb_id=kb_id, content=rc.text,
                               chunk_index=i, meta=json.dumps(meta, ensure_ascii=False)))
            s.commit()

        kb.retriever.index(self._load_chunks(kb_id))
        return {"document_id": doc_id, "filename": filename, "chunks_count": len(raw_chunks)}

    def list_documents(self, kb_id: str) -> list[dict]:
        self.get_kb(kb_id)
        db = get_db()
        with db.session() as s:
            rows = s.query(DocumentRow).filter(DocumentRow.kb_id == kb_id).all()
        return [{"id": r.id, "filename": r.filename, "status": r.status,
                 "chunks_count": r.chunks_count} for r in rows]

    # ---- 检索 ----
    def search(self, kb_id: str, query: str, top_k: int = 5) -> list[SearchResult]:
        kb = self.get_kb(kb_id)
        return kb.retriever.search(query, top_k)

    def _load_chunks(self, kb_id: str) -> list[Chunk]:
        db = get_db()
        with db.session() as s:
            rows = s.query(ChunkRow).filter(ChunkRow.kb_id == kb_id).order_by(ChunkRow.chunk_index).all()
        return [Chunk(id=r.id, text=r.content, index=r.chunk_index,
                      metadata=json.loads(r.meta or "{}")) for r in rows]
