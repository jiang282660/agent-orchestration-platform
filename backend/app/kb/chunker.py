"""文本分块：语义优先（标题/段落边界）+ 固定长度兜底。"""

import re
from dataclasses import dataclass, field

_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)


@dataclass
class Chunk:
    text: str
    index: int = 0
    id: str = ""
    metadata: dict = field(default_factory=dict)


def _split_units(text: str) -> list[str]:
    """按标题与空行切分为语义单元。"""
    text = _HEADING.sub(lambda m: "\n\n" + m.group(0), text)
    parts = [p.strip() for p in re.split(r"\n\s*\n", text)]
    return [p for p in parts if p]


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """对超长单元做固定长度 + 重叠切分。"""
    step = chunk_size - overlap if chunk_size > overlap else chunk_size
    return [text[i:i + chunk_size] for i in range(0, len(text), step)]


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[Chunk]:
    units = _split_units(text)
    chunks: list[str] = []
    buf = ""
    for u in units:
        if len(u) <= chunk_size:
            if not buf:
                buf = u
            elif len(buf) + 1 + len(u) <= chunk_size:
                buf = buf + "\n" + u
            else:
                chunks.append(buf)
                buf = u
        else:
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.extend(_hard_split(u, chunk_size, chunk_overlap))
    if buf:
        chunks.append(buf)
    return [Chunk(text=c, index=i) for i, c in enumerate(chunks) if c.strip()]
