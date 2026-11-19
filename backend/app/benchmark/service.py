"""基准集（golden set）：定义必覆盖要点 + 覆盖度评估。"""

import json
import re
from datetime import datetime

import jieba

from app.db import BenchmarkItemRow, BenchmarkRow, BenchmarkRunRow, gen_id, get_db

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w一-鿿]+")


class BenchmarkService:
    def create_benchmark(self, name: str, description: str = "",
                         workflow_name: str = "research_report", items: list[dict] | None = None) -> dict:
        b_id = gen_id("bench")
        items = items or []
        db = get_db()
        with db.session() as s:
            s.add(BenchmarkRow(id=b_id, name=name, description=description, workflow_name=workflow_name))
            for it in items:
                s.add(BenchmarkItemRow(id=gen_id("item"), benchmark_id=b_id,
                                       question=it["question"],
                                       golden_points=json.dumps(it["golden_points"], ensure_ascii=False)))
            s.commit()
        return {"id": b_id, "name": name, "workflow_name": workflow_name, "item_count": len(items)}

    def get_benchmark(self, b_id: str) -> dict:
        db = get_db()
        with db.session() as s:
            row = s.get(BenchmarkRow, b_id)
            if not row:
                raise KeyError(f"基准集不存在: {b_id}")
            items = s.query(BenchmarkItemRow).filter(BenchmarkItemRow.benchmark_id == b_id).all()
        return {
            "id": row.id, "name": row.name, "description": row.description,
            "workflow_name": row.workflow_name,
            "items": [{"id": i.id, "question": i.question,
                       "golden_points": json.loads(i.golden_points)} for i in items],
        }

    def list_benchmarks(self) -> list[dict]:
        db = get_db()
        with db.session() as s:
            rows = s.query(BenchmarkRow).all()
        return [{"id": r.id, "name": r.name, "description": r.description,
                 "workflow_name": r.workflow_name} for r in rows]

    def record_run(self, b_id: str, item_id: str, coverage_score: float, detail: dict) -> dict:
        db = get_db()
        rid = gen_id("brun")
        with db.session() as s:
            s.add(BenchmarkRunRow(id=rid, benchmark_id=b_id, item_id=item_id,
                                  coverage_score=coverage_score,
                                  detail=json.dumps(detail, ensure_ascii=False),
                                  created_at=datetime.now().isoformat(timespec="seconds")))
            s.commit()
        return {"id": rid, "coverage_score": coverage_score}


def compute_coverage(draft: str, golden_points: list[str]) -> tuple[float, list[str], list[str]]:
    """确定性覆盖度：golden point 的关键词命中过半即视为覆盖。"""
    covered, missing = [], []
    for p in golden_points:
        if _point_covered(draft or "", p):
            covered.append(p)
        else:
            missing.append(p)
    score = round(len(covered) / len(golden_points), 3) if golden_points else 0.0
    return score, covered, missing


def _point_covered(draft: str, point: str) -> bool:
    d = _norm(draft)
    p = _norm(point)
    if not p:
        return False
    # 1) 直接包含（最严格）
    if p in d:
        return True
    # 2) 内容词命中率（jieba 分词，忽略单字与虚词）
    tokens = [t for t in jieba.cut(point) if len(t) > 1]
    if tokens:
        hit = sum(1 for t in tokens if t in draft)
        if hit / len(tokens) >= 0.5:
            return True
    # 3) 字符 2-gram 软匹配：容忍近义改写/语序微调（确定性，仍无 LLM 依赖）
    pg = _bigrams(p)
    if pg:
        overlap = sum(1 for g in pg if g in d) / len(pg)
        if overlap >= 0.6:
            return True
    return False


def _norm(text: str) -> str:
    return _WS.sub("", _PUNCT.sub("", text or ""))


def _bigrams(text: str) -> list[str]:
    return [text[i:i + 2] for i in range(len(text) - 1)]
