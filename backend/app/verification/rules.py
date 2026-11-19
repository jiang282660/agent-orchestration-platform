"""规则核查：确定性的结果验证（不依赖 LLM）。"""

import re


def rule_check(draft: str) -> dict:
    text = draft or ""
    checks = {
        "非空": bool(text.strip()),
        "有章节结构": bool(re.search(r"(^|\n)#{1,6}\s", text)) or ("一、" in text or "二、" in text),
        "含引用标注": ("来源" in text) or ("【来源" in text),
        "篇幅充足": len(text) >= 200,
    }
    passed = sum(1 for v in checks.values() if v)
    return {"checks": checks, "passed": passed, "total": len(checks),
            "score": round(passed / len(checks), 3)}
