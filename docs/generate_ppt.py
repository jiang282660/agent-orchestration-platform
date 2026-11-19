# -*- coding: utf-8 -*-
"""生成「Agent 编排调度平台」方案讲解 PPT（16:9，14 页）。"""
from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ASSETS = Path(__file__).parent / "assets"
OUT = Path(__file__).parent / "答辩PPT.pptx"

PRIMARY = RGBColor(0x0A, 0x59, 0xF7)
DARK = RGBColor(0x1F, 0x23, 0x29)
MUTED = RGBColor(0x64, 0x6A, 0x73)
ACCENT = RGBColor(0xF7, 0x6B, 0x15)
LIGHT = RGBColor(0xEE, 0xF4, 0xFF)
GREEN = RGBColor(0x1D, 0x9A, 0x52)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "微软雅黑"


def _set_run(run, size=14, bold=False, color=DARK):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = rPr.makeelement(qn('a:ea'), {})
        rPr.append(ea)
    ea.set('typeface', FONT)


def add_text(slide, x, y, w, h, lines, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for ln in lines:
        if isinstance(ln, str):
            ln = (ln, 14, False, DARK)
        text, size, bold, color = ln
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(6)
        r = p.add_run(); r.text = text
        _set_run(r, size=size, bold=bold, color=color)
    return tb


def add_bullets(slide, x, y, w, h, items):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for it in items:
        text = it if isinstance(it, str) else it[0]
        level = 0 if isinstance(it, str) else it[1]
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.level = level
        p.space_after = Pt(8)
        r = p.add_run()
        r.text = ("• " if level == 0 else "– ") + text
        _set_run(r, size=14 if level == 0 else 12.5, color=DARK if level == 0 else MUTED)
    return tb


def header(slide, title):
    add_text(slide, 0.6, 0.35, 12, 0.6, [(title, 26, True, DARK)])
    bar = slide.shapes.add_shape(1, Inches(0.6), Inches(1.05), Inches(0.5), Inches(0.06))
    bar.fill.solid(); bar.fill.fore_color.rgb = PRIMARY; bar.line.fill.background()


def add_pic(slide, path, x, y, w=None, h=None):
    kw = {}
    if w: kw['width'] = Inches(w)
    if h: kw['height'] = Inches(h)
    return slide.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)


def card(slide, x, y, w, h, title, body, tcolor=PRIMARY):
    box = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.color.rgb = PRIMARY; box.line.width = Pt(1.2)
    add_text(slide, x + 0.25, y + 0.18, w - 0.5, 0.5, [(title, 16, True, tcolor)])
    add_text(slide, x + 0.25, y + 0.8, w - 0.5, h - 0.95, [(body, 12.5, False, DARK)])


prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

# 1 封面
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = PRIMARY; bg.line.fill.background()
add_text(s, 1, 2.3, 11.3, 1.0, [("Agent 编排调度平台", 48, True, WHITE)], align=PP_ALIGN.CENTER)
add_text(s, 1, 3.4, 11.3, 0.6, [("大模型 Agent 工具编排调度平台 · 方案讲解", 20, False, WHITE)], align=PP_ALIGN.CENTER)
add_text(s, 1, 4.3, 11.3, 0.5, [("多智能体协作的编排 · 调度 · 执行 · 验证", 15, False, RGBColor(0xD6, 0xE4, 0xFF))], align=PP_ALIGN.CENTER)
add_text(s, 1, 6.3, 11.3, 0.5, [("2026 年 11 月", 13, False, RGBColor(0xC7, 0xD7, 0xFE))], align=PP_ALIGN.CENTER)

# 2 选题背景与痛点
s = prs.slides.add_slide(BLANK)
header(s, "选题背景与痛点")
add_text(s, 0.6, 1.5, 12.1, 0.5, [("LLM 正从「单轮问答」走向「多智能体自主协作」，Agent Harness 框架兴起", 16, False, DARK)])
add_bullets(s, 0.6, 2.2, 12.1, 4.6, [
    ("单轮问答缺乏自主决策 —— 无法自主拆解任务、调用工具、多步执行", 0),
    ("编排复杂 —— 现成框架封装过深，编排/调度机制不透明、难解释", 0),
    ("结果不可信 —— 大模型幻觉、缺乏溯源与验证", 0),
    ("工具调用碎片化 —— 缺乏统一、可插拔的工具接入规范", 0),
    ("难以量化评估 —— 缺少客观指标衡量优化前后效果", 0),
])

# 3 场景与需求（六大能力）
s = prs.slides.add_slide(BLANK)
header(s, "业务场景与核心需求")
add_text(s, 0.6, 1.5, 12.1, 0.5, [("场景：基于知识库的多智能体研究报告生成", 16, True, PRIMARY)])
caps = [("知识库集成", "文档解析→分块→混合检索"), ("Agent 团队", "六角色声明式定义"),
        ("工作流编排", "DSL 定义 DAG"), ("动态调度", "运行时图展开"),
        ("Self-Loop", "执行→评估→反馈→重执行"), ("结果验证", "规则+评分+事实+基准集")]
for i, (t, d) in enumerate(caps):
    x = 0.6 + (i % 3) * 4.1
    y = 2.2 + (i // 3) * 2.4
    card(s, x, y, 3.85, 2.0, t, d)

# 4 总体架构
s = prs.slides.add_slide(BLANK)
header(s, "平台总体架构")
add_pic(s, ASSETS / "00-architecture.png", 0.7, 1.5, w=12.0)
add_text(s, 0.6, 6.9, 12.1, 0.4, [("前端 → API → 自研编排内核 → 能力层 → 存储层，五层解耦", 12.5, False, MUTED)], align=PP_ALIGN.CENTER)

# 5 技术选型
s = prs.slides.add_slide(BLANK)
header(s, "技术选型")
rows = [("编排内核", "自研（不依赖 LangGraph），评分点全链路可控可解释"),
        ("LLM", "DeepSeek（OpenAI 兼容）+ 指数退避重试"),
        ("检索", "BM25 + bge 语义向量 RRF 混合检索"),
        ("存储", "SQLite 元数据 + runs/run_steps 运行轨迹"),
        ("前端", "Vue3 + Element Plus + Vite（SSE 实时看板）")]
for i, (t, d) in enumerate(rows):
    y = 1.6 + i * 1.1
    box = s.shapes.add_shape(1, Inches(0.6), Inches(y), Inches(12.1), Inches(0.95))
    box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.fill.background()
    add_text(s, 0.9, y + 0.12, 2.2, 0.5, [(t, 15, True, PRIMARY)])
    add_text(s, 3.3, y + 0.22, 9.2, 0.6, [(d, 13.5, False, DARK)])

# 6 Agent 角色定义
s = prs.slides.add_slide(BLANK)
header(s, "Agent 角色定义（六角色团队）")
add_bullets(s, 0.6, 1.5, 6.0, 4.5, [
    ("planner 规划者 —— 拆解任务大纲", 0),
    ("retriever 检索者 —— 多轮检索 + 来源", 0),
    ("analyzer 分析者 —— 提炼论点与证据", 0),
    ("writer 撰写者 —— 生成正文 + 引用标注", 0),
    ("reviewer 审校者 —— 四维评分 + 反馈", 0),
    ("verifier 验证者 —— 事实核查", 0),
    ("每个 Agent 具备 ReAct 多步工具循环能力", 0),
])
add_text(s, 6.9, 1.5, 5.8, 4.5, [
    ("Agent 声明式定义", 15, True, PRIMARY),
    ("id / name / role_prompt / tools", 13, False, DARK),
    ("llm_config / output_schema / max_steps", 13, False, DARK),
    ("", 10, False, DARK),
    ("结构化输出可靠性", 15, True, PRIMARY),
    ("response_format=json_object", 13, False, DARK),
    ("Pydantic 校验 + 失败重试 ≤2 次", 13, False, DARK),
    ("失败降级标记 degraded，绝不静默产出非法结构", 13, False, DARK),
])

# 7 工作流编排
s = prs.slides.add_slide(BLANK)
header(s, "工作流编排（DSL → DAG）")
add_text(s, 0.6, 1.5, 12.1, 0.5, [("以 YAML/JSON 声明 DAG，节点类型：agent / expand / loop / rule", 15, True, PRIMARY)])
add_bullets(s, 0.6, 2.2, 12.1, 4.6, [
    ("depends_on 声明依赖，「所有依赖完成即就绪」触发节点", 0),
    ("reads/writes 声明与共享 RunState 的读写契约，全程记录变更历史", 0),
    ("支持顺序、并行、条件分支、子工作流、循环", 0),
    ("环检测 + 拓扑校验，保证 DAG 合法性", 0),
    ("节点间通过 RunState 传递数据，可回溯、可复现、可画执行轨迹", 0),
])

# 8 调度算法 + Self-Loop
s = prs.slides.add_slide(BLANK)
header(s, "调度算法与自我循环机制")
card(s, 0.6, 1.5, 6.0, 2.4, "动态调度", "递归依赖等待 + 备忘录 + 双重检查锁；expand 运行时按 planner 子任务动态扇出并行执行；Semaphore 限流（默认 4）")
card(s, 0.6, 4.1, 6.0, 2.4, "Self-Loop", "执行→评估→反馈→重执行；阈值 + 轮次上限；评分曲线全程记录")
card(s, 6.9, 1.5, 6.0, 2.4, "实测评分曲线", "[0.72 → 0.82]：首轮未达标 → 反馈重写 → 二轮达标退出")
card(s, 6.9, 4.1, 6.0, 2.4, "容错", "LLM 指数退避重试；节点级异常兜底，单次抖动不中断整次运行")

# 9 结果验证
s = prs.slides.add_slide(BLANK)
header(s, "结果验证与反馈优化")
add_bullets(s, 0.6, 1.5, 12.1, 5.0, [
    ("规则核查（确定性）—— 非空/章节结构/引用标注/篇幅，rule_gate 节点", 0),
    ("LLM 评分（reviewer）—— 相关性/准确性/完整性/流畅性 四维 + 评分锚点", 0),
    ("事实核查（verifier）—— 逐条核查断言是否有据，区分有据/无据", 0),
    ("基准集（golden set）—— 必覆盖要点清单，量化优化前后覆盖度提升", 0),
    ("反馈闭环：生成 → 评估 → 反馈 → 重写 → 再评估", 0),
])

# 10 系统界面（总览 + 看板）
s = prs.slides.add_slide(BLANK)
header(s, "系统界面：总览 + 任务看板")
add_pic(s, ASSETS / "01-overview.png", 0.5, 1.5, w=6.4)
add_pic(s, ASSETS / "03b-run-live.png", 7.1, 1.5, w=5.9)
add_text(s, 0.5, 6.85, 6.4, 0.4, [("六角色团队 + 工作流 DAG 可视化", 11, False, MUTED)], align=PP_ALIGN.CENTER)
add_text(s, 7.1, 6.85, 5.9, 0.4, [("执行时间线 + Self-Loop 评分曲线", 11, False, MUTED)], align=PP_ALIGN.CENTER)

# 11 系统界面（知识库 + 基准）
s = prs.slides.add_slide(BLANK)
header(s, "系统界面：知识库 + 基准评估")
add_pic(s, ASSETS / "02-knowledge-base.png", 0.5, 1.5, w=6.4)
add_pic(s, ASSETS / "04-benchmark.png", 7.1, 1.5, w=5.9)
add_text(s, 0.5, 6.85, 6.4, 0.4, [("文档入库与混合检索", 11, False, MUTED)], align=PP_ALIGN.CENTER)
add_text(s, 7.1, 6.85, 5.9, 0.4, [("golden set 覆盖度评估", 11, False, MUTED)], align=PP_ALIGN.CENTER)

# 12 运行效果（实测）
s = prs.slides.add_slide(BLANK)
header(s, "运行效果（真实 DeepSeek 实测）")
rows = [("Self-Loop 评分曲线", "[0.72 → 0.82]（反馈提分，两轮达标）"),
        ("规则核查", "4/4 通过"),
        ("事实核查", "通过率 0.93（20 有据 / 6 无据）"),
        ("基准覆盖度", "1.0（10/10 要点覆盖）")]
for i, (t, d) in enumerate(rows):
    y = 1.7 + i * 1.2
    box = s.shapes.add_shape(1, Inches(0.9), Inches(y), Inches(11.5), Inches(1.0))
    box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.fill.background()
    add_text(s, 1.2, y + 0.2, 3.2, 0.5, [(t, 15, True, PRIMARY)])
    add_text(s, 4.6, y + 0.22, 7.6, 0.6, [(d, 14, False, DARK)])

# 13 AI 使用说明
s = prs.slides.add_slide(BLANK)
header(s, "人工智能使用说明（LLM / RAG / MCP）")
card(s, 0.6, 1.5, 6.0, 2.5, "LLM（DeepSeek）", "作用：规划/生成/评分/核查；贡献：自主决策核心；局限：幻觉与评分随机性 → 检索注入 + 三层验证缓解")
card(s, 0.6, 4.2, 6.0, 2.5, "RAG（混合检索）", "作用：语义+关键词检索注入证据；贡献：降幻觉、可溯源；局限：依赖文档质量")
card(s, 6.9, 1.5, 6.0, 2.5, "工具抽象 / MCP", "作用：统一工具接入与执行；当前自定义 Tool + function-calling，预留 MCP 扩展点")
card(s, 6.9, 4.2, 6.0, 2.5, "Embedding（bge）", "作用：本地向量化语义检索；贡献：离线可用、中文好；语义不可用时降级 BM25")

# 14 总结
s = prs.slides.add_slide(BLANK)
header(s, "总结")
add_text(s, 0.6, 1.7, 12.1, 0.5, [("贯通六大能力：知识库集成 · Agent 团队 · 工作流编排 · 动态调度 · Self-Loop · 结果验证", 16, True, PRIMARY)])
add_bullets(s, 0.6, 2.5, 12.1, 3.0, [
    ("自研编排内核，全链路自主可控、可解释、可演示", 0),
    ("真实 DeepSeek 端到端跑通，评分/验证/覆盖度指标完整", 0),
    ("全部源码随方案交付，评审可一键复现", 0),
])
add_text(s, 0.6, 6.2, 12.1, 0.6, [("谢谢观看 · 敬请指正", 22, True, PRIMARY)], align=PP_ALIGN.CENTER)

prs.save(OUT)
print("已生成 PPT:", OUT, "| 页数:", len(prs.slides._sldIdLst))
