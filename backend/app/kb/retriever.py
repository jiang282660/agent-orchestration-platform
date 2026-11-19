"""检索器抽象：BM25 关键词 + 语义向量 + RRF 混合检索。

语义检索后端可插拔：优先 sentence-transformers，其次 fastembed（ONNX、轻量、免 torch）。
两者均不可用时自动降级为纯 BM25，保证链路可离线跑通。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import jieba
import numpy as np
from rank_bm25 import BM25Okapi

from app.kb.chunker import Chunk

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"


@dataclass
class SearchResult:
    chunk_id: str
    text: str
    score: float
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"chunk_id": self.chunk_id, "text": self.text, "score": round(self.score, 4),
                "metadata": self.metadata}


class BaseRetriever(ABC):
    @abstractmethod
    def index(self, chunks: list[Chunk]) -> None: ...

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[SearchResult]: ...

    def semantic_available(self) -> bool:
        """是否启用了语义向量检索（用于界面/接口展示与混合检索降级判断）。"""
        return False


class BM25Retriever(BaseRetriever):
    """关键词检索：jieba 分词 + BM25，零模型下载、可离线运行。"""

    def __init__(self):
        self._chunks: list[Chunk] = []
        self._bm25: BM25Okapi | None = None

    def index(self, chunks: list[Chunk]) -> None:
        self._chunks = list(chunks)
        if self._chunks:
            self._bm25 = BM25Okapi([list(jieba.cut(c.text)) for c in self._chunks])
        else:
            self._bm25 = None

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(list(jieba.cut(query)))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        # score != 0 表示有词元重叠；单文档时 BM25 分数可能为负，不能用 > 0 过滤
        return [
            SearchResult(chunk_id=self._chunks[i].id, text=self._chunks[i].text,
                         score=float(scores[i]), metadata=self._chunks[i].metadata)
            for i in order if scores[i] != 0
        ]


class _Embedder:
    """可插拔文本向量化后端：sentence-transformers → fastembed → 不可用。"""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._backend: str | None = None
        self.available = False
        self.error: str | None = None
        self._tried = False

    def _load(self) -> None:
        if self._model is not None or self._tried:
            return
        self._tried = True
        # 后端 1：sentence-transformers（方案文档首选）
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._backend = "sentence-transformers"
        except Exception as e:
            self.error = f"sentence-transformers: {e}"
            # 后端 2：fastembed（ONNX，轻量，免 torch）
            try:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=self.model_name)
                self._backend = "fastembed"
                self.error = None
            except Exception as e2:
                self.error += f"; fastembed: {e2}"
                self._model = None
        self.available = self._model is not None

    def encode(self, texts: list[str]) -> np.ndarray:
        self._load()
        if not self.available:
            raise RuntimeError(self.error or "embedding model unavailable")
        vecs = np.asarray(self._model.encode(texts), dtype="float32")
        # 归一化，使点积等价于余弦相似度
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms


class SemanticRetriever(BaseRetriever):
    """语义向量检索：embedding + 余弦相似度（内存向量，无外部向量库依赖）。"""

    def __init__(self, model_name: str | None = None):
        self._embedder = _Embedder(model_name or DEFAULT_EMBEDDING_MODEL)
        self._chunks: list[Chunk] = []
        self._vectors: np.ndarray | None = None

    def index(self, chunks: list[Chunk]) -> None:
        self._chunks = list(chunks)
        if not self._chunks:
            self._vectors = None
            return
        try:
            self._vectors = self._embedder.encode([c.text for c in self._chunks])
        except Exception:
            self._vectors = None

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if self._vectors is None or not self._embedder.available:
            return []
        q = self._embedder.encode([query])[0]
        scores = self._vectors @ q  # 已归一化，等价余弦相似度
        order = np.argsort(-scores)[:top_k]
        return [
            SearchResult(chunk_id=self._chunks[i].id, text=self._chunks[i].text,
                         score=float(scores[i]), metadata=self._chunks[i].metadata)
            for i in order
        ]

    def semantic_available(self) -> bool:
        return self._embedder.available


class HybridRetriever(BaseRetriever):
    """混合检索：BM25 关键词 + 语义向量，RRF 融合（k=60）。语义不可用时退化为纯 BM25。"""

    def __init__(self, model_name: str | None = None):
        self.bm25 = BM25Retriever()
        self.semantic = SemanticRetriever(model_name)
        self._rrf_k = 60

    def index(self, chunks: list[Chunk]) -> None:
        self.bm25.index(chunks)
        self.semantic.index(chunks)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        bm25_res = self.bm25.search(query, top_k=top_k * 3)
        if not self.semantic.semantic_available():
            return bm25_res[:top_k]
        sem_res = self.semantic.search(query, top_k=top_k * 3)

        rrf: dict[str, float] = {}
        meta: dict[str, SearchResult] = {}
        for rank, r in enumerate(bm25_res):
            rrf[r.chunk_id] = rrf.get(r.chunk_id, 0.0) + 1.0 / (self._rrf_k + rank + 1)
            meta.setdefault(r.chunk_id, r)
        for rank, r in enumerate(sem_res):
            rrf[r.chunk_id] = rrf.get(r.chunk_id, 0.0) + 1.0 / (self._rrf_k + rank + 1)
            meta.setdefault(r.chunk_id, r)
        ordered = sorted(rrf.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        return [
            SearchResult(chunk_id=cid, text=meta[cid].text, score=round(rrf[cid], 4),
                         metadata=meta[cid].metadata)
            for cid, _ in ordered
        ]

    def semantic_available(self) -> bool:
        return self.semantic.semantic_available()


def build_retriever(retriever_type: str = "hybrid", embedding_model: str | None = None) -> BaseRetriever:
    """按类型构建检索器：bm25 | semantic | hybrid。"""
    t = (retriever_type or "hybrid").lower()
    if t == "semantic":
        return SemanticRetriever(embedding_model)
    if t == "hybrid":
        return HybridRetriever(embedding_model)
    return BM25Retriever()
