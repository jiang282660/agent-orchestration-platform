"""文档解析：把上传的字节内容解析为纯文本。"""

import io

SUPPORTED_EXTS = {".txt", ".md", ".markdown", ".pdf"}


def parse_document(filename: str, content: bytes) -> str:
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext in (".txt", ".md", ".markdown"):
        return content.decode("utf-8", errors="replace")
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    raise ValueError(f"不支持的文件类型: {filename}（支持: {', '.join(sorted(SUPPORTED_EXTS))}）")
