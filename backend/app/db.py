"""SQLite 持久化层（SQLAlchemy 2.x）。"""

import os
import uuid
from pathlib import Path

from sqlalchemy import Column, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class KnowledgeBaseRow(Base):
    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True)
    name = Column(String)
    description = Column(String, default="")
    chunk_size = Column(Integer, default=500)
    chunk_overlap = Column(Integer, default=50)
    created_at = Column(String)


class DocumentRow(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    kb_id = Column(String, index=True)
    filename = Column(String)
    status = Column(String, default="done")
    chunks_count = Column(Integer, default=0)
    created_at = Column(String)


class ChunkRow(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)
    doc_id = Column(String, index=True)
    kb_id = Column(String, index=True)
    content = Column(Text)
    chunk_index = Column(Integer)
    meta = Column("metadata", Text, default="{}")  # 属性名避开 SQLAlchemy 保留字段 metadata


class BenchmarkRow(Base):
    __tablename__ = "benchmarks"

    id = Column(String, primary_key=True)
    name = Column(String)
    description = Column(String, default="")
    workflow_name = Column(String, default="research_report")


class BenchmarkItemRow(Base):
    __tablename__ = "benchmark_items"

    id = Column(String, primary_key=True)
    benchmark_id = Column(String, index=True)
    question = Column(Text)
    golden_points = Column(Text)  # JSON 数组


class BenchmarkRunRow(Base):
    __tablename__ = "benchmark_runs"

    id = Column(String, primary_key=True)
    benchmark_id = Column(String, index=True)
    item_id = Column(String)
    coverage_score = Column(Float)
    detail = Column(Text, default="{}")
    created_at = Column(String)


class RunRow(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True)
    workflow_name = Column(String)
    input_json = Column(Text, default="{}")
    status = Column(String, default="running")
    result_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(String)
    finished_at = Column(String, nullable=True)


class RunStepRow(Base):
    __tablename__ = "run_steps"

    id = Column(String, primary_key=True)
    run_id = Column(String, index=True)
    node_id = Column(String)
    agent_id = Column(String, nullable=True)
    status = Column(String, default="done")
    output_json = Column(Text, nullable=True)
    tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    iteration = Column(Integer, nullable=True)
    degraded = Column(Integer, default=0)
    created_at = Column(String)


class Database:
    def __init__(self, url: str | None = None):
        url = url or os.environ.get("DB_URL", "sqlite:///data/app.db")
        if url.startswith("sqlite:///"):
            Path(url[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(url, connect_args={"check_same_thread": False})
        self._Session = sessionmaker(bind=self._engine)
        Base.metadata.create_all(self._engine)

    def session(self):
        return self._Session()


_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
