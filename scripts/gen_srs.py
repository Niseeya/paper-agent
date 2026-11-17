# -*- coding: utf-8 -*-
"""生成《需求规格说明书》V1.0。"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor, Twips

TITLE = "基于 RAG 与多 Skill 协同的学术论文研究与生成 AI 智能体系统的设计与实现"
# 仓库根目录下的 docs/，勿写死本机绝对路径
OUT = str(Path(__file__).resolve().parents[1] / "docs" / "需求规格说明书_V1.0.docx")

FRS = []
NFRS = []
ACS = []


def set_run_font(run, cn="宋体", en="Times New Roman", size=12, bold=False, color=None):
    run.bold = bold
    run.italic = False
    run.font.size = Pt(size)
    run.font.name = en
    if color is not None:
        run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), en)
    rFonts.set(qn("w:hAnsi"), en)
    rFonts.set(qn("w:eastAsia"), cn)
    rFonts.set(qn("w:cs"), en)


def shade_cell(cell, fill):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:shd")):
        tcPr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def set_cell_border(cell):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn("w:tcBorders"))
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)
    for edge in ("top", "left", "bottom", "right"):
        el = tcBorders.find(qn(f"w:{edge}"))
        if el is None:
            el = OxmlElement(f"w:{edge}")
            tcBorders.append(el)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "BFBFBF")


def set_cell_text(cell, text, bold=False, size=10.5, center=False, color=None, fill=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, color=color)
    if fill:
        shade_cell(cell, fill)
    set_cell_border(cell)
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    vAlign = tcPr.find(qn("w:vAlign"))
    if vAlign is None:
        vAlign = OxmlElement("w:vAlign")
        tcPr.append(vAlign)
    vAlign.set(qn("w:val"), "center")


def prevent_row_split(row):
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    trPr.append(cant)


def mark_header_row(row):
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    trPr.append(tbl_header)


def set_table_widths(table, widths):
    table.autofit = False
    table.allow_autofit = False
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    total = sum(widths)
    tblW.set(qn("w:w"), str(total))
    tblW.set(qn("w:type"), "dxa")
    grid = tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for child in list(grid):
            grid.remove(child)
    else:
        grid = OxmlElement("w:tblGrid")
        tblPr.addnext(grid)
    for w in widths:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(w))
        grid.append(gc)
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcW = tcPr.find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW")
                tcPr.append(tcW)
            tcW.set(qn("w:w"), str(widths[i]))
            tcW.set(qn("w:type"), "dxa")


def add_field(paragraph, instruction):
    r1 = paragraph.add_run()
    b = OxmlElement("w:fldChar")
    b.set(qn("w:fldCharType"), "begin")
    r1._r.append(b)
    r2 = paragraph.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instruction
    r2._r.append(it)
    r3 = paragraph.add_run()
    s = OxmlElement("w:fldChar")
    s.set(qn("w:fldCharType"), "separate")
    r3._r.append(s)
    r4 = paragraph.add_run(" ")
    set_run_font(r4, size=10.5)
    r5 = paragraph.add_run()
    e = OxmlElement("w:fldChar")
    e.set(qn("w:fldCharType"), "end")
    r5._r.append(e)


def configure(doc):
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.header_distance = Cm(0.8)
    section.footer_distance = Cm(0.8)
    section.different_first_page_header_footer = False

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    rPr = normal.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rFonts.set(qn("w:eastAsia"), "宋体")
    pf = normal.paragraph_format
    pf.line_spacing = 1.15
    pf.space_after = Pt(6)
    pf.space_before = Pt(0)

    specs = {
        "Heading 1": (16, "黑体", 16, 8),
        "Heading 2": (14, "黑体", 12, 6),
        "Heading 3": (12, "黑体", 10, 4),
    }
    for name, (size, cn, before, after) in specs.items():
        st = doc.styles[name]
        st.font.name = "Times New Roman"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
        st.font.italic = False
        rPr = st.element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        rFonts.set(qn("w:ascii"), "Times New Roman")
        rFonts.set(qn("w:hAnsi"), "Times New Roman")
        rFonts.set(qn("w:eastAsia"), cn)
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)
        st.paragraph_format.line_spacing = 1.15
        st.paragraph_format.keep_with_next = True

    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    hp.paragraph_format.space_after = Pt(2)
    run = hp.add_run(TITLE + "  |  需求规格说明书")
    set_run_font(run, size=9, color=RGBColor(0x55, 0x55, 0x55))
    pPr = hp._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "BFBFBF")
    pBdr.append(bottom)
    pPr.append(pBdr)

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("第 ")
    set_run_font(r, size=9, color=RGBColor(0x55, 0x55, 0x55))
    add_field(fp, " PAGE ")
    r2 = fp.add_run(" 页")
    set_run_font(r2, size=9, color=RGBColor(0x55, 0x55, 0x55))

    core = doc.core_properties
    core.title = TITLE + "需求规格说明书"
    core.subject = "软件需求规格说明书 SRS V1.0"
    core.category = "SRS"
    core.language = "zh-CN"
    core.comments = "项目题目已冻结。本文描述完整产品的可观察行为与验收标准。"


def h1(doc, text):
    p = doc.add_heading(text, level=1)
    for run in p.runs:
        set_run_font(run, cn="黑体", size=16, bold=True, color=RGBColor(0x1A, 0x1A, 0x1A))
    return p


def h2(doc, text):
    p = doc.add_heading(text, level=2)
    for run in p.runs:
        set_run_font(run, cn="黑体", size=14, bold=True, color=RGBColor(0x1A, 0x1A, 0x1A))
    return p


def h3(doc, text):
    p = doc.add_heading(text, level=3)
    for run in p.runs:
        set_run_font(run, cn="黑体", size=12, bold=True, color=RGBColor(0x1A, 0x1A, 0x1A))
    return p


def para(doc, text, size=12, bold=False, center=False, after=6, before=0, indent=False):
    p = doc.add_paragraph()
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = 1.15
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.74)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold)
    return p


def bullets(doc, items):
    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.4)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run("·  " + item)
        set_run_font(run, size=12)


def code_block(doc, caption, text):
    if caption:
        para(doc, caption, size=10.5, bold=True, after=3)
    table = doc.add_table(rows=1, cols=1)
    cell = table.cell(0, 0)
    cell.text = ""
    shade_cell(cell, "F7F7F7")
    set_cell_border(cell)
    lines = text.strip("\n").split("\n")
    first = True
    for line in lines:
        if first:
            p = cell.paragraphs[0]
            first = False
        else:
            p = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(line if line else " ")
        set_run_font(run, cn="宋体", en="Consolas", size=8)
    set_table_widths(table, [9638])
    para(doc, "", size=6, after=2)


def add_table(doc, caption, headers, rows, widths):
    if caption:
        para(doc, caption, size=10.5, bold=True, after=3, before=4)
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for i, head in enumerate(headers):
        set_cell_text(table.rows[0].cells[i], head, bold=True, size=10.5, center=True,
                      color=RGBColor(0xFF, 0xFF, 0xFF), fill="1F4E79")
    mark_header_row(table.rows[0])
    prevent_row_split(table.rows[0])
    for r_idx, row in enumerate(rows):
        fill = "F3F6F9" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, value in enumerate(row):
            set_cell_text(table.rows[r_idx + 1].cells[c_idx], str(value), size=10.5, fill=fill)
        prevent_row_split(table.rows[r_idx + 1])
    set_table_widths(table, widths)
    return table


def fr_table(doc, caption, rows):
    for row in rows:
        FRS.append(row)
    add_table(
        doc,
        caption,
        ["编号", "需求", "详细要求"],
        [row[:3] for row in rows],
        [1400, 2200, 6038],
    )


def build():
    doc = Document()
    configure(doc)
    cover(doc)
    doc.add_page_break()
    chapter1(doc)
    chapter2(doc)
    chapter3(doc)
    chapter4(doc)
    chapter5(doc)
    chapter6(doc)
    chapter7(doc)
    chapter8(doc)
    chapter9(doc)
    chapter10(doc)
    chapter11(doc)
    chapter12(doc)
    appendix(doc)
    doc.save(OUT)
    print("FR", len(FRS), "NFR", len(NFRS), "AC", len(ACS))
    print(OUT)


def cover(doc):
    para(doc, "", size=12, after=6)
    para(doc, TITLE, size=18, bold=True, center=True, after=4)
    para(doc, "需求规格说明书", size=18, bold=True, center=True, after=2)
    para(doc, "Software Requirements Specification", size=12, center=True, after=2)
    para(doc, "V1.0", size=14, bold=True, center=True, after=10)
    para(doc, "文档编号：SRS-RAG-SKILL-PAPER-V1.0", size=12, center=True, after=2)
    para(doc, "编制日期：2026年11月16日", size=12, center=True, after=2)
    para(doc, "状态：现行", size=12, center=True, after=12)

    add_table(
        doc,
        "表 0-1  文档属性",
        ["文档属性", "内容"],
        [
            ["项目名称", TITLE],
            ["文档类型", "软件需求规格说明书（SRS）"],
            ["文档版本", "V1.0"],
            ["产品形态", "Web、Android、微信小程序。iOS 可选，不进入最低交付"],
            ["编制依据", "IEEE 830、ISO/IEC/IEEE 29148 的需求规格说明结构"],
            ["目标用户", "科研人员、研究生、学术作者"],
            ["知识范围", "部署时配置的单一研究领域"],
            ["数据来源", "预置论文包、用户上传论文"],
            ["核心技术特征", "RAG + 主控工作流 + 多 Skill；关键节点人工确认"],
            ["系统结构", "前后端分离的模块化单体，不拆分微服务"],
            ["开发参考", "仓库根目录 AGENTS.md。实现顺序和默认技术栈以该文件为准"],
            ["容量口径", "单机部署，已索引文本型 PDF 不超过 200 篇"],
        ],
        [2400, 7238],
    )
    para(
        doc,
        "本说明书描述这个产品的全部业务规则、可观察行为、数据、接口和验收标准。所列需求都属于产品本身，不按阶段裁剪。类名、函数和服务器脚本由设计说明书规定。更换仍满足本文的模型、向量库或 Web 框架，不构成需求变更。开发时的目录、默认技术栈和实现顺序见 AGENTS.md。",
        indent=True,
    )
    add_table(
        doc,
        "表 0-2  修订记录",
        ["版本", "日期", "说明", "状态"],
        [["V1.0", "2026-11-16", "按完整产品编写。需求不分期，开发对照见 AGENTS.md", "现行"]],
        [1200, 1600, 5438, 1400],
    )
    h1(doc, "目录")
    para(doc, "目录覆盖第 1 章至附录。在 Word 中右键下方域，执行“更新域”，即可生成带页码的目录。", size=12)
    p = doc.add_paragraph()
    add_field(p, ' TOC \\o "1-3" \\h \\z \\u ')


def chapter1(doc):
    h1(doc, "1. 项目概述")
    h2(doc, "1.1 项目背景")
    para(
        doc,
        "学术论文写作包含文献定位、观点比较、结构规划、带证据的表述和参考文献整理。通用大语言模型可以生成流畅文字，但在指定研究领域中经常缺少可回看的文献依据，也可能写出知识库中不存在的题名、作者或年份。把检索、核查、规划和修改放在同一次模型调用中，错误难以定位，作者也无法在大纲、引用和定稿等节点作出确认。",
        indent=True,
    )
    para(
        doc,
        "本课题的项目题目为“" + TITLE + "”。建设对象是一套面向单一研究领域的论文研究与生成系统：以预置论文包和用户上传论文构成领域知识库，以检索增强约束内容来源，以多项 Skill 分别完成检索、分析、大纲、写作、润色、引用核查和导出，由主控工作流按状态调度，并在关键节点等待作者确认。",
        indent=True,
    )
    h2(doc, "1.2 项目建设目标")
    bullets(doc, [
        "建立单一研究领域的论文知识库，来源限于预置论文包和用户上传论文。",
        "提供关键词、语义和混合检索，并返回可定位到页码和原文片段的证据。",
        "支持单篇要素提取和多篇对比，对比单元缺少证据时显示“库内未找到”。",
        "在作者确认大纲之后，按章节生成带证据关联的正文草稿。",
        "提供不改变数值、专有名词、引用和结论方向的学术润色，并保留修改对照。",
        "管理参考文献，阻止知识库之外的文献成为正式引用。",
        "导出 Markdown、Word、LaTeX 和 PDF。",
        "用有限步数的工作流调度 Skill，记录每次执行，并在失败时给出原因。",
    ])
    h2(doc, "1.3 项目定位")
    para(
        doc,
        "本系统是上述课题所实现的软件。课题论文由项目组撰写。系统向科研人员、研究生和学术作者提供领域内的研究辅助和受控生成：检索、比较、大纲、章节草稿、润色和导出都留在作者可审核的链路上。作者对选题、论点、数据解释和最终提交文本负责。",
        indent=True,
    )
    add_table(
        doc,
        "表 1-1  产品定位",
        ["维度", "产品规定"],
        [
            ["用户", "科研人员、研究生、学术作者；另设系统管理员"],
            ["知识基础", "单一领域的预置论文包与用户上传论文，经切片和向量索引后供检索"],
            ["调度方式", "主控工作流识别意图、拆分任务并调用已登记 Skill"],
            ["执行单元", "最低交付为 S1～S10。润色保留，但不能替代这十个 Skill"],
            ["质量机制", "证据链、引用闸门、支持程度标记、人工确认记录"],
            ["生成边界", "先确认大纲，再生成章节；定稿导出只接受已核验引用"],
        ],
        [2400, 7238],
    )
    h2(doc, "1.4 产品范围")
    para(doc, "下表是产品的完整范围。研究领域名称、术语表和预置论文清单写在部署配置中，全系统只装载这一个领域。", indent=True)
    add_table(
        doc,
        "表 1-2  产品范围",
        ["范围", "说明"],
        [
            ["研究领域", "一个由部署配置指定的研究领域，包含领域名称、术语表和预置论文清单"],
            ["知识来源", "管理员导入的预置论文，以及用户上传并同意进入公用知识库的 PDF。索引后所有登录用户可检索"],
            ["用户类型", "普通用户、系统管理员"],
            ["核心功能", "文献调研、多篇对比、研究脉络、论文规划、章节生成、学术润色、引用管理"],
            ["导出格式", "Markdown、Word、LaTeX、BibTeX、PDF"],
            ["文献核验", "库内真实性、证据片段、支持程度；带 DOI 的文献做外部元数据核验"],
            ["自动化程度", "检索、分析和起草由系统完成。大纲确认、润色确认和定稿导出由作者完成"],
            ["运行环境", "单机部署。页面、检索、解析、生成和导出满足第 4 章指标"],
        ],
        [2400, 7238],
    )
    h2(doc, "1.5 系统边界")
    bullets(doc, [
        "对 Google Scholar、CNKI、万方等数据库进行实时全文抓取、爬取或无授权接入。",
        "未经大纲确认和引用核验，自动生成整篇论文并直接作为定稿。",
        "以降低查重率、规避相似性检测或代替作者署名完成为目标的改写功能。",
        "IDE 插件和浏览器插件。未交付 iOS 不影响验收。",
        "图表自动分析、独立公式编辑器、代码复现和实验复现。",
        "多个研究领域并行、跨学科知识库和领域知识图谱。",
        "多个智能体自由对话式协作，以及无步数上限的互调用。",
        "面向公众的生产容量、在线支付和商业计费。",
    ])
    h2(doc, "1.6 术语与缩略语")
    add_table(
        doc,
        "表 1-3  术语",
        ["术语", "说明"],
        [
            ["RAG", "检索增强生成。回答和正文草稿所依据的文献片段来自当前项目检索范围"],
            ["Agent / 主控工作流", "识别用户意图、选择 Skill、推进状态并在人工节点停止的控制程序"],
            ["Skill", "一项可单独测试的专业能力，具有明确输入、输出和失败行为"],
            ["Embedding", "把文本切片映射为向量，用于语义检索"],
            ["Reranker", "对初检结果再次排序的模型，检索结果交给问答和写作前使用"],
            ["Chunk", "带有论文、页码和字符或页内位置的知识切片"],
            ["证据片段", "一条被引用句子所绑定的原文切片"],
            ["正式引用", "写入参考文献表、并在正文中编号的引用。必须来自公用知识库中已索引论文"],
            ["无证据草稿", "没有绑定证据片段的生成句子。可以留在草稿中，不能带正式引用"],
            ["支持程度", "支持、部分支持、未找到证据。由引用核查 Skill 给出"],
            ["定稿导出", "全部正式引用通过库内存在性检查和证据绑定后的 Markdown、Word、LaTeX 或 PDF"],
            ["草稿导出", "允许包含未核验内容的导出，页眉或文首标明辅助生成草稿"],
            ["公用知识库", "预置论文和用户已索引上传论文组成的同一检索库。登录用户可检索和查看原文"],
            ["预置论文包", "管理员导入公用知识库的领域论文，普通用户不能删除"],
            ["LLM", "大语言模型。具体供应商和型号不在本文冻结"],
            ["SRS", "软件需求规格说明书"],
        ],
        [2400, 7238],
    )
    h2(doc, "1.7 假设与依赖")
    bullets(doc, [
        "作者会在大纲、润色和定稿导出三个节点查看结果。系统不把未确认文本当作已完成论文。",
        "预置论文和用户上传论文是文本型 PDF，或可被 OCR 识别的扫描件。加密且无法提取文本的文件记为解析失败。",
        "部署配置至少包含一种对话模型、一种嵌入模型和一种重排序模型，可以是外部 API 或本地服务，并且可以切换。",
        "外部模型服务会按供应商政策处理请求文本。首次上传和首次生成前，界面展示数据处理说明，用户确认后才发送正文或论文全文。",
        "默认参考文献格式为 GB/T 7714。产品同时提供 APA、IEEE 和 MLA。",
    ])
    add_table(
        doc,
        "表 1-4  部署配置",
        ["编号", "配置", "影响", "何时必须具备"],
        [
            ["CFG-01", "研究领域名称、术语表、预置论文清单", "知识库、Prompt 和评测样本", "系统投入使用前"],
            ["CFG-02", "每篇预置论文的来源类型与授权记录", "能否导入预置包", "该文件导入前"],
            ["CFG-03", "对话、嵌入、重排序和 OCR 的端点", "检索、生成和扫描件解析", "对应功能启用前"],
            ["CFG-04", "公用知识库不超过 200 篇已索引文本型 PDF", "第 4 章性能指标的测量条件", "验收时"],
        ],
        [1200, 3600, 2838, 2000],
    )


def chapter2(doc):
    h1(doc, "2. 用户角色与业务场景")
    h2(doc, "2.1 用户角色")
    add_table(
        doc,
        "表 2-1  角色",
        ["角色", "权限与职责"],
        [
            ["普通用户", "注册登录；上传论文进入公用知识库；创建和管理本人项目；检索公用知识库；进行分析、大纲、写作、润色、引用核查和导出"],
            ["系统管理员", "管理用户状态和角色；导入、更新、下线预置论文包；配置模型端点、配额和参考文献默认格式；查看任务与运行状态"],
        ],
        [2400, 7238],
    )
    para(doc, "系统不设访客写入权限。未登录用户只能看到登录页和系统用途说明。", indent=True)
    h2(doc, "2.2 权限控制要求")
    bullets(doc, [
        "需要登录的接口必须校验访问令牌。管理接口必须校验管理员角色。",
        "密码只保存慢哈希结果，不保存明文。令牌密钥放在服务端环境配置中，不写入仓库。",
        "普通用户只能修改本人的项目、大纲、正文、润色和导出文件。",
        "用户上传并索引成功的论文进入公用知识库。其他登录用户可以检索和查看原文，不能删除。",
        "预置论文由管理员导入公用知识库。普通用户不能删除或替换预置文件。",
        "检索范围是公用知识库中已索引论文，不包含其他用户的大纲、正文和导出文件。",
        "管理员查看用户正文或导出文件时，系统记录操作者、时间、对象和原因。",
        "禁用用户后，该用户的令牌立即失效，其文件仍保留至管理员执行删除或达到保留期。",
    ])
    h2(doc, "2.3 用户核心需求")
    add_table(
        doc,
        "表 2-2  核心需求与对应能力",
        ["用户需要完成的事", "系统提供的能力", "主要需求"],
        [
            ["了解领域内已有研究", "在公用知识库中检索和问答", "FR-040～FR-051"],
            ["筛选相关文献", "关键词、语义、混合检索和元数据过滤", "FR-040～FR-045"],
            ["比较不同论文", "单篇要素和多篇对比矩阵", "FR-060、FR-061"],
            ["寻找可继续研究的问题", "带证据的研究不足建议", "FR-065"],
            ["安排论文结构", "大纲生成、编辑和确认", "FR-082～FR-085"],
            ["形成章节文字", "按节生成、改写和手动编辑", "FR-100～FR-106"],
            ["整理学术表达", "三档润色和修改对照", "FR-120～FR-128"],
            ["检查引用", "库内真实性、证据绑定和支持程度", "FR-140～FR-146"],
            ["得到可编辑文档", "Markdown 与 Word，增强格式另计", "FR-161～FR-166"],
        ],
        [2800, 4200, 2638],
    )
    h2(doc, "2.4 核心业务场景")
    scenarios = [
        ("UC-01  上传论文并进入公用知识库",
         "普通用户已登录。",
         "用户选择一个或多个 PDF，勾选同意进入公用知识库，提交上传。系统校验格式和大小，显示逐文件进度，解析文本、题名、作者、摘要和页码，完成切片与索引。列表中看到“已索引”。另一名登录用户可以检索到该论文。",
         "文件损坏、加密或无法识别时，该文件标记解析失败并说明原因，不影响同批其他文件。公用库已有相同文件时提示重复，不重复建索引。",
         "公用知识库新增可检索论文。上传者的项目正文不会因此被公开。",
         "FR-020～FR-030"),
        ("UC-02  围绕研究主题做文献调研",
         "公用知识库至少有一篇已索引论文。",
         "用户输入研究问题。系统在公用知识库中混合检索，返回答案、相关论文和证据片段。用户可按作者、年份过滤，并可打开原文位置。",
         "没有可靠片段时，系统说明证据不足，不给出确定性结论。",
         "问答记录保存到项目，证据可再次打开。",
         "FR-040～FR-051"),
        ("UC-03  对比多篇论文",
         "用户已选择 2～8 篇已索引论文。",
         "系统按研究问题、方法、对象或数据、主要结论、局限生成对比矩阵，并保存到项目。",
         "某一格在所选论文中找不到依据时填写“库内未找到”，不补写推测。",
         "项目中存在可回看的对比结果。",
         "FR-060、FR-061、FR-066"),
        ("UC-04  形成研究思路和论文大纲",
         "项目已有检索或对比结果，用户已填写题目、论文类型和研究问题。",
         "系统给出研究问题、目标、方法和创新点建议，并生成到二级或三级标题的大纲。每节附带写作意图和关联文献。用户可增删改章节并保存版本。",
         "建议缺少证据时标记“证据不足”。用户未确认前，大纲状态保持“待确认”。",
         "存在一个可确认的大纲版本。",
         "FR-080～FR-085"),
        ("UC-05  依据文献证据撰写正文",
         "大纲状态为“已确认”，相关章节已关联文献或允许用户先写无证据草稿。",
         "用户选择一个章节生成草稿，或对选中段落提出续写、改写、扩展、精简。带引用的句子绑定证据，并显示支持程度。",
         "模型超时或输出无法解析时保留已有正文，提示重试。无证据句子标记为无证据草稿。",
         "章节草稿写入正文，并生成新版本。",
         "FR-100～FR-106"),
        ("UC-06  润色并核查引用",
         "存在正文草稿。",
         "用户选择轻度、学术或深度润色。系统给出对照、修改原因，用户确认后替换。用户另行发起引用核查，查看缺失引用、库外引用和支持程度。",
         "用户要求以降重或规避检测为目标时，系统拒绝该请求，并仍可提供不改变原意的学术润色。",
         "确认后的润色写入版本记录。核查报告可导出前复看。",
         "FR-120～FR-128、FR-143～FR-146"),
        ("UC-07  导出文档",
         "正文、大纲和参考文献数据已保存。",
         "用户选择 Markdown、Word、LaTeX 或 PDF。草稿导出立即生成，并带草稿标识。定稿导出前系统复查正式引用。",
         "存在未绑定证据的正式引用时，定稿导出停止并列出句子。转换失败时保留源数据并显示原因。",
         "用户获得可下载文件，导出任务可查询。",
         "FR-160～FR-166"),
    ]
    for title, pre, main, exc, post, fr in scenarios:
        h3(doc, title)
        add_table(
            doc,
            "",
            ["项", "内容"],
            [
                ["参与者", "普通用户"],
                ["前置条件", pre],
                ["主流程", main],
                ["异常流程", exc],
                ["后置条件", post],
                ["关联需求", fr],
            ],
            [1800, 7838],
        )
    h2(doc, "2.5 典型业务流程")
    para(doc, "论文项目按以下状态推进：草稿、资料准备、大纲待确认、写作中、核验中、可导出。状态只随对应业务动作变化，不能由前端随意指定。", indent=True)
    code_block(doc, "图 2-1  论文项目主流程", """
flowchart TD
    A[创建论文项目] --> B[检索公用知识库或上传 PDF]
    B --> C[解析、切片并建立索引]
    C --> D[检索、问答与文献分析]
    D --> E[生成大纲]
    E --> F{作者确认大纲}
    F -->|否| E
    F -->|是| G[按章节生成草稿]
    G --> H[手动编辑]
    H --> I[润色对照并确认]
    I --> J[引用存在性与证据核查]
    J --> K{定稿条件是否满足}
    K -->|否| H
    K -->|是| L[导出 Markdown 或 Word]
""")


def chapter3(doc):
    h1(doc, "3. 系统总体功能需求")
    para(doc, "功能需求按模块编号。每条需求应能对应到输入、输出、规则和异常。异常的统一行为见第 9 章。", indent=True)

    h2(doc, "3.1 用户与项目管理模块")
    h3(doc, "3.1.1 用户管理")
    para(doc, "系统区分普通用户和管理员。注册信息至少包含用户名、邮箱和密码。用户名与邮箱在系统内唯一。密码长度不少于 8 位，并同时包含字母和数字。", indent=True)
    h3(doc, "3.1.2 论文项目管理")
    para(doc, "项目是大纲、正文、检索记录、分析结果和导出任务的边界。创建时记录题目、论文类型、目标格式和所属领域。论文类型至少包括综述、实证研究和设计与实现。目标格式至少包括 Markdown 和 Word。", indent=True)
    h3(doc, "3.1.3 项目工作区")
    para(doc, "工作区集中进入文献、大纲、正文、引用和版本。大纲和正文各自至少保留最近 10 个版本，恢复旧版本时生成新版本，不覆盖历史。", indent=True)
    fr_table(doc, "表 3-1  用户与项目需求", [
        ["FR-001", "用户注册", "校验用户名、邮箱和密码；用户名与邮箱唯一；重复时返回明确字段错误", "高"],
        ["FR-002", "用户登录", "校验密码哈希并签发访问令牌；连续失败 5 次后锁定 10 分钟", "高"],
        ["FR-003", "用户退出", "客户端清除令牌；服务端使当前令牌失效", "高"],
        ["FR-004", "个人资料", "用户可修改显示名和联系说明，不能自行提升角色", "中"],
        ["FR-005", "角色权限", "普通用户与管理员的接口和页面按第 2.2 节隔离", "高"],
        ["FR-006", "创建项目", "录入题目、论文类型、目标格式；领域取自当前部署且只读展示", "高"],
        ["FR-007", "修改项目", "可修改题目、类型、格式和简介；已有正文保留", "高"],
        ["FR-008", "删除项目", "二次确认后删除项目及其大纲、正文、分析、引用和导出记录；不删除已进入公用知识库的论文", "高"],
        ["FR-009", "项目列表与状态", "按更新时间展示本人项目及第 2.5 节状态", "高"],
        ["FR-010", "使用公用知识库", "项目检索、对比和引用直接使用公用知识库，不为用户单独复制一份私有论文库", "高"],
        ["FR-011", "工作区入口", "同一项目内可进入文献、大纲、正文、引用、润色和导出", "高"],
        ["FR-012", "版本保留", "大纲和正文各保留最近 10 版，支持查看时间和恢复", "高"],
    ])

    h2(doc, "3.2 文档上传与知识库管理模块")
    h3(doc, "3.2.1 论文上传")
    para(doc, "上传格式为 PDF。单文件不超过 30 MB，单次批量不超过 20 个。上传前必须勾选“我有权上传，并同意该论文进入公用知识库，供其他登录用户检索和查看”。未勾选则拒绝。服务端重新生成存储文件名，不使用用户原始路径。索引成功前，其他用户看不到该文件。", indent=True)
    h3(doc, "3.2.2 文档解析")
    para(doc, "文本型 PDF 提取全文、题名、作者、摘要、年份和页码。能识别章节时按章节切分，否则按页切分并标记“章节未识别”。公式和表格至少保留所在页码；无法转为文本时保存区域占位，不丢弃该页。扫描件走 OCR。置信度低于配置阈值时标记解析失败，禁止把低置信文本标成已索引。", indent=True)
    h3(doc, "3.2.3 知识库构建")
    para(doc, "解析成功后进行空白清理、切片、向量化和关键词索引。切片保存论文标识、页码、在文中的顺序和原文。元数据至少包括题名、作者、年份、来源类型。相同文件哈希，或题名与第一作者同时高度一致时，提示重复并跳过新索引。", indent=True)
    h3(doc, "3.2.4 知识库管理")
    para(doc, "论文状态包括待解析、解析中、解析成功、解析失败、索引中、已索引、索引失败。预置论文和用户上传论文在索引成功后进入同一公用知识库。上传者或管理员删除论文后，该论文从所有用户的检索结果消失，已被引用的正文句子改为“来源已删除”。项目大纲和正文不进入公用知识库。", indent=True)
    fr_table(doc, "表 3-2  知识库需求", [
        ["FR-020", "PDF 上传校验", "仅接受 PDF；超过 30 MB、扩展名与内容不符或未同意进入公用知识库时拒绝", "高"],
        ["FR-021", "批量与重试", "单次最多 20 个文件；显示每个文件进度；失败文件可单独重试", "高"],
        ["FR-022", "元数据提取", "提取题名、作者、摘要和年份；失败时允许用户手工补录后再索引", "高"],
        ["FR-023", "章节与页码", "记录页码和切片位置；章节识别失败时按页切分并标记", "高"],
        ["FR-024", "扫描件 OCR", "低置信结果不得进入已索引；向用户显示识别不完整", "中"],
        ["FR-025", "切片与向量索引", "清洗后切片、向量化并建立可按论文过滤的索引", "高"],
        ["FR-026", "关键词与过滤字段", "保存题名、作者、年份、关键词，供检索过滤", "高"],
        ["FR-027", "去重", "公用库中文件哈希相同，或题名加第一作者高度一致时提示重复，不重复索引", "高"],
        ["FR-028", "状态可见", "公用库列表展示解析状态、索引状态、上传者和失败原因", "高"],
        ["FR-029", "删除与下线", "上传者可删除自己的论文，管理员可下线任意论文；删除后所有用户都检索不到", "高"],
        ["FR-030", "公用知识库", "预置论文与用户上传论文进入同一检索库；其他用户不能删除；项目文稿不入库", "高"],
        ["FR-031", "预置包管理", "仅管理员可导入、更新和下线预置论文，并记录来源类型、导入人和时间", "高"],
    ])

    h2(doc, "3.3 RAG 智能检索模块")
    h3(doc, "3.3.1 检索功能")
    para(doc, "检索只发生在公用知识库里状态为已索引的论文中。系统同时提供关键词检索、语义检索和混合检索。过滤条件包括作者、年份区间和单篇论文。", indent=True)
    h3(doc, "3.3.2 检索优化")
    para(doc, "初检结果按相关度排序，去掉重复切片，并可合并相邻切片补足上下文。默认向问答和写作返回不超过 8 条证据，管理员可配置上限，硬上限为 20。混合检索之后必须经过重排序，再把结果交给问答和写作。", indent=True)
    h3(doc, "3.3.3 智能问答")
    para(doc, "问答必须依据本次检索到的片段。回答列出相关论文、证据片段和页码。多篇联合回答逐条对应来源。证据不足以支持结论时，回答为证据不足，不使用模型记忆补写确定性说法。", indent=True)
    h3(doc, "3.3.4 引用溯源")
    para(doc, "每条进入正文的正式引用保存来源论文、页码、原文片段和生成句子的对应关系。界面可从句子打开证据。", indent=True)
    fr_table(doc, "表 3-3  检索与溯源需求", [
        ["FR-040", "关键词检索", "在公用知识库中按题名、摘要、关键词和正文检索", "高"],
        ["FR-041", "语义检索", "用查询向量在公用知识库的切片中检索", "高"],
        ["FR-042", "混合检索", "合并关键词与语义结果并去重", "高"],
        ["FR-043", "元数据过滤", "支持作者、年份区间和指定论文过滤", "高"],
        ["FR-044", "重排序", "混合检索结果经重排序模型排序后，再交给问答和写作", "高"],
        ["FR-045", "结果数量与上下文", "默认不超过 8 条证据，可合并相邻切片，硬上限 20", "高"],
        ["FR-046", "知识库问答", "回答仅依据本次检索片段，并附带论文与页码", "高"],
        ["FR-047", "多篇联合回答", "综合多篇时保持每条陈述可回到具体论文", "高"],
        ["FR-048", "证据展示", "展示论文、页码和原文片段，点击可定位", "高"],
        ["FR-049", "证据不足", "无可靠片段时提示证据不足，不输出确定性结论", "高"],
        ["FR-050", "生成与证据关联", "正式引用句保存并展示证据关联", "高"],
        ["FR-051", "范围限定", "可以检索其他用户已放入公用库的论文；不得检索其他用户的大纲、正文和导出文件", "高"],
    ])

    h2(doc, "3.4 文献分析模块")
    para(doc, "分析结果分为“提取”和“建议”。提取只改写论文中能够定位的内容。研究不足、研究机会和创新点一律标记为建议。", indent=True)
    fr_table(doc, "表 3-4  文献分析需求", [
        ["FR-060", "单篇要素提取", "提取背景、问题、方法、实验或设计、结果、结论、局限；原文没有的项标为原文未识别", "高"],
        ["FR-061", "多篇对比矩阵", "对 2～8 篇论文比较问题、方法、对象或数据、主要结论和局限；空缺填库内未找到", "高"],
        ["FR-062", "观点差异", "指出所选论文对同一问题的不同表述，并各自附证据", "中"],
        ["FR-063", "主题归纳", "把项目文献分成若干方向，每类列出依据论文", "中"],
        ["FR-064", "发展脉络", "按年份整理方法或主题变化，样本不足时说明无法判断趋势", "低"],
        ["FR-065", "研究不足建议", "每条建议附证据，或标明证据不足；不把建议写成已证实结论", "中"],
        ["FR-066", "分析结果保存", "分析可保存、重新打开，并记录所用论文和时间", "高"],
    ])

    h2(doc, "3.5 论文规划与大纲生成模块")
    para(doc, "大纲生成可以使用项目内证据。研究问题、方法建议和创新点以建议呈现。大纲未经确认时，状态为待确认。", indent=True)
    fr_table(doc, "表 3-5  规划与大纲需求", [
        ["FR-080", "研究输入", "接收题目、论文类型、研究问题、目标格式；缺题目或研究问题时不生成大纲", "高"],
        ["FR-081", "研究规划建议", "给出问题、目标、方法和创新点建议，并区分有证据与证据不足", "中"],
        ["FR-082", "大纲生成", "生成一级至三级标题，每节包含写作意图", "高"],
        ["FR-083", "大纲编辑与版本", "可调整顺序、层级和标题，保存版本", "高"],
        ["FR-084", "章节关联证据", "每节可关联论文和证据；关联可手工增删", "高"],
        ["FR-085", "大纲确认闸门", "仅作者确认后的大纲允许按章节批量生成；确认前只允许单段试写", "高"],
    ])

    h2(doc, "3.6 论文正文辅助写作模块")
    para(doc, "写作 Skill 只能把正式引用指向公用知识库中已索引论文。模型输出中出现库外题名、作者或年份时，系统删除该正式引用，并把句子标为无证据草稿。", indent=True)
    fr_table(doc, "表 3-6  正文写作需求", [
        ["FR-100", "按节生成", "对已确认大纲中的选定章节生成草稿，输入包含章节意图和已关联证据", "高"],
        ["FR-101", "指令修改", "支持续写、改写、扩展、精简和重组；涉及事实或引用的改写重新绑定证据", "高"],
        ["FR-102", "手动编辑与保存", "正文可直接编辑；停止输入后自动保存，并保留版本", "高"],
        ["FR-103", "支持程度", "每个正式引用句显示支持、部分支持或未找到证据", "高"],
        ["FR-104", "无证据草稿", "没有证据的生成句可以保留，但不能分配正式引用编号", "高"],
        ["FR-105", "质量提示", "检查明显的章节间重复和缺少论据的判断句，只提示，不自动删除", "中"],
        ["FR-106", "禁止无人确认成篇", "不提供跳过大纲确认后一次生成全部章节并标为定稿的操作", "高"],
    ])

    h2(doc, "3.7 学术语言润色模块")
    para(doc, "润色分为轻度、学术和深度三档。三档都不得改变数字、专有名词、引用编号和结论方向。用户若要求改变结论或事实，该请求转入写作改写，并重新绑定证据。系统不提供降重档、查重规避参数或相似性目标。", indent=True)
    fr_table(doc, "表 3-7  润色需求", [
        ["FR-120", "基础纠错", "修正拼写、语法、标点和明显病句，并给出对照", "高"],
        ["FR-121", "学术表达", "替换口语化表达，统一术语；术语以领域术语表和原文为准", "高"],
        ["FR-122", "段落衔接", "调整衔接和段落顺序时保持原有命题", "中"],
        ["FR-123", "三档润色", "提供轻度、学术、深度三档；深度档仍遵守不改变事实的规则", "高"],
        ["FR-124", "中英对照润色", "可将中文润色为英文或反向处理，同时保留术语和引用", "中"],
        ["FR-125", "修改确认", "展示原文、结果、高亮差异和修改原因；用户确认后才替换正文", "高"],
        ["FR-126", "原意约束", "不得改动数字、引用、专有名词和结论极性；无法遵守时拒绝本次润色", "高"],
        ["FR-127", "拒绝降重请求", "请求目标为降低查重率或规避检测时拒绝，并说明可改为学术润色", "高"],
        ["FR-128", "撤销与恢复", "确认后的润色可撤销到上一版本", "高"],
    ])

    h2(doc, "3.8 参考文献与引用管理模块")
    para(doc, "正式引用的核验分两级。L1：文献存在于公用知识库，且题名、作者、年份与库内元数据一致。L2：引用句至少绑定一条该文献的证据片段。两级都通过，引用才算核验通过。文献带有 DOI 时，再查询外部元数据。外部查询失败只标记“外部未核验”，不否定已经通过的 L1 和 L2。", indent=True)
    fr_table(doc, "表 3-8  引用管理需求", [
        ["FR-140", "文献表与去重", "由正式引用生成文献表；同一论文只出现一次", "高"],
        ["FR-141", "元数据与 DOI", "保存作者、年份、题名、来源和 DOI；DOI 可空", "高"],
        ["FR-142", "正文引用编号", "插入、删除引用后自动重排编号，并同步文献表", "高"],
        ["FR-143", "库内真实性", "公用知识库以外的文献不能成为正式引用", "高"],
        ["FR-144", "元数据一致", "正式引用的题名、作者、年份与库内记录不一致时标为未通过", "高"],
        ["FR-145", "支持性检查", "给出支持、部分支持或未找到证据，并保留证据片段", "高"],
        ["FR-146", "缺失提醒", "判断句没有证据、或引用未通过 L1/L2 时在核查报告中列出", "高"],
        ["FR-147", "GB/T 7714", "默认按 GB/T 7714 输出参考文献", "高"],
        ["FR-148", "APA 与 IEEE", "可切换 APA、IEEE 格式", "中"],
        ["FR-149", "MLA", "可切换为 MLA 格式", "高"],
        ["FR-150", "外部 DOI 核验", "文献带有 DOI 时查询外部元数据；失败时标记外部未核验，且不否定已通过的 L1 和 L2", "高"],
    ])

    h2(doc, "3.9 文档编辑与导出模块")
    para(doc, "系统内部以统一文档结构保存题目、作者信息、章节、段落、引用标识、证据标识和参考文献。Markdown、Word、LaTeX 和 PDF 都从该结构导出，避免多套正文。图片、表格和公式保留标题、编号和来源页码；能提取文本或 LaTeX 时一并保存。", indent=True)
    fr_table(doc, "表 3-9  导出需求", [
        ["FR-160", "统一文档结构", "题目、章节、段落、引用、证据和文献表来自同一项目数据", "高"],
        ["FR-161", "Markdown 导出", "保留标题层级、段落、表格文本、公式文本和引用标记", "高"],
        ["FR-162", "Word 导出", "导出 DOCX，包含标题样式、正文、自动目录和参考文献", "高"],
        ["FR-163", "图公式占位", "无法排版的图、表、公式保留编号、说明和来源页码", "中"],
        ["FR-164", "LaTeX 导出", "导出 TEX 和 BibTeX；模板可配置。失败不影响 Markdown 和 Word", "中"],
        ["FR-165", "PDF 导出", "由 Word 或 LaTeX 转换；失败时给出转换器错误，不生成空文件充当成功", "中"],
        ["FR-166", "草稿与定稿", "草稿带“辅助生成草稿”标识。定稿要求全部正式引用通过 L1 和 L2，否则拒绝并列出问题句", "高"],
        ["FR-167", "页眉信息", "导出文件页眉包含项目题目和导出时间", "中"],
    ])

    h2(doc, "3.10 多 Skill 协同与工作流模块")
    para(doc, "最低交付登记 S1～S10：主题结构化、文献检索、论文解析、多篇对比、方向分类、研究空白、大纲、章节写作、论文检查、文档导出。润色另行登记，不计入这十个 Skill。主控工作流只能调用已登记 Skill。意图无法判断时先追问，不调用章节写作或导出。每个 Skill 必须能在不启动完整工作流的情况下单独测试。工作流调用成功，不等于该 Skill 已经通过测试。", indent=True)
    para(doc, "单节点失败后最多重试 2 次。一次用户任务最多 12 步。同一步的相同检索请求不重复调用模型。引用核验失败时停止在核查报告，不自动循环重写整节。", indent=True)
    fr_table(doc, "表 3-10  工作流需求", [
        ["FR-180", "意图识别", "识别检索问答、单篇分析、多篇对比、大纲、写作、润色、引用核查、导出；不能识别时追问", "高"],
        ["FR-181", "Skill 路由", "按意图调用已登记 Skill，并向用户展示当前 Skill 名称", "高"],
        ["FR-182", "人工节点", "大纲确认、润色确认、定稿导出三处必须等待用户动作", "高"],
        ["FR-183", "重试与终止", "节点最多重试 2 次，任务最多 12 步；超限后终止并保留已完成结果", "高"],
        ["FR-184", "执行记录", "记录任务输入摘要、Skill、模型标识、开始结束时间、结果状态和错误", "高"],
        ["FR-185", "失败可见", "超时、格式错误、步数超限和证据缺失都返回可理解原因", "高"],
        ["FR-186", "禁止核验死循环", "引用未通过时不自动反复重写；由用户修改后再重新核查", "高"],
        ["FR-187", "S1～S10 独立测试", "每个 Skill 用规定输入单独运行，并核对图示验收条件：结构化主题、真实文献及来源、正文和章节、有证据的对比、研究方向分类、候选空白及依据、可编辑大纲、带真实引用的正文、引用和逻辑问题、可打开的 DOCX 与 PDF", "高"],
        ["FR-188", "测试隔离", "工作流集成通过不能把任一 Skill 记为已通过。S1～S10 的测试报告分别给出结果", "高"],
    ])


def chapter4(doc):
    h1(doc, "4. 非功能性需求")
    para(doc, "下列指标在单机部署、公用知识库不超过 200 篇已索引文本型 PDF、单用户操作时测量。外部模型服务的网络波动记入测试条件，不把供应商故障算作功能通过。", indent=True)
    h2(doc, "4.1 准确性要求")
    nfr_rows = [
        ["NFR-001", "正式引用只能来自项目已索引论文，系统不得把模型补写的文献写入文献表", "高"],
        ["NFR-002", "问答中的事实性陈述和正文正式引用句提供证据片段；做不到时标明证据不足或无证据草稿", "高"],
        ["NFR-003", "正式引用可打开到来源论文、页码和片段", "高"],
        ["NFR-004", "无法验证的内容以提示或标记出现，不写成已核验事实", "高"],
        ["NFR-005", "润色不改变数字、专有名词、引用和结论方向", "高"],
        ["NFR-006", "研究不足和创新点使用“建议”类型，不显示为已证实发现", "高"],
    ]
    NFRS.extend(nfr_rows)
    add_table(doc, "表 4-1  准确性", ["编号", "要求"], [r[:2] for r in nfr_rows], [1600, 8038])

    h2(doc, "4.2 性能要求")
    perf = [
        ["NFR-007", "普通页面与不含模型的保存操作", "P95 不高于 1 秒", "本地功能数据"],
        ["NFR-008", "项目内混合检索", "P95 不高于 8 秒", "已索引论文不超过 200 篇"],
        ["NFR-009", "知识问答完整响应", "P95 不高于 20 秒", "单用户，证据不超过 8 条"],
        ["NFR-010", "大纲生成", "P95 不高于 30 秒", "二级大纲，单用户"],
        ["NFR-011", "单节草稿", "P95 不高于 60 秒", "约 800 字，已关联证据"],
        ["NFR-012", "文本型 PDF 解析至可检索", "20 页以内不高于 60 秒", "不含扫描件 OCR"],
        ["NFR-013", "文档导出", "Markdown 或 Word 的 P95 不高于 15 秒；LaTeX 或 PDF 不高于 60 秒", "一篇含目录和参考文献的文稿"],
        ["NFR-014", "并发", "不少于 10 个登录会话，不少于 3 个生成任务排队", "单机部署"],
    ]
    NFRS.extend([[a, b + "：" + c, "高"] for a, b, c, _ in perf])
    add_table(doc, "表 4-2  性能", ["编号", "场景", "目标", "条件"],
              [[a, b, c, d] for a, b, c, d in perf], [1200, 2800, 2638, 3000])

    h2(doc, "4.3 安全性要求")
    sec = [
        ["NFR-015", "登录接口校验身份；管理接口校验角色；失败返回统一的无权提示", "高"],
        ["NFR-016", "大纲、正文、润色和导出按项目所有者隔离。已索引上传论文对登录用户可检索，未索引文件不对其他用户可见", "高"],
        ["NFR-017", "未登录不能下载论文。登录用户可打开公用知识库中的已索引原文，不能通过猜测地址访问未索引文件", "高"],
        ["NFR-018", "部署启用 HTTPS。密码哈希存储。模型密钥只出现在服务端环境配置", "高"],
        ["NFR-019", "用户可删除本人项目和本人上传的论文。删除论文时移除文件、切片和向量。删除项目不移除公用知识库中的论文", "高"],
        ["NFR-020", "首次上传前说明文件会进入公用知识库并可能发送给模型服务，用户确认后才上传。首次生成前确认后才发送正文", "高"],
        ["NFR-021", "日志记录任务标识和错误，不记录论文全文、正文全文和密钥", "高"],
    ]
    NFRS.extend(sec)
    add_table(doc, "表 4-3  安全", ["编号", "要求"], [r[:2] for r in sec], [1600, 8038])

    h2(doc, "4.4 可维护性要求")
    maint = [
        ["NFR-022", "对话模型、嵌入模型、重排序模型和 OCR 服务可通过配置更换，更换后 FR 的外部行为保持不变", "高"],
        ["NFR-023", "新增 Skill 时不修改无关 Skill 的输入输出契约", "高"],
        ["NFR-024", "Prompt 按 Skill 保存版本、修改时间和启用状态", "高"],
        ["NFR-025", "检索条数、重排序开关、切片长度和任务步数上限可配置", "高"],
        ["NFR-026", "知识库、工作流、写作编辑和导出在模块化单体中保持独立模块边界", "高"],
    ]
    NFRS.extend(maint)
    add_table(doc, "表 4-4  可维护性", ["编号", "要求"], [r[:2] for r in maint], [1600, 8038])

    h2(doc, "4.5 可用性要求")
    use = [
        ["NFR-027", "超过 2 秒的解析、检索、生成和导出显示进行中状态，并可查看失败原因", "高"],
        ["NFR-028", "上传失败可对单文件重试，不要求整批重传", "高"],
        ["NFR-029", "正文自动保存；浏览器刷新后恢复最近成功保存的内容", "高"],
        ["NFR-030", "大纲和正文可恢复到保留期内的历史版本", "高"],
        ["NFR-031", "界面文字使用简体中文。生成内容的语言跟随用户指定的写作语言", "高"],
    ]
    NFRS.extend(use)
    add_table(doc, "表 4-5  可用性", ["编号", "要求"], [r[:2] for r in use], [1600, 8038])

    h2(doc, "4.6 可扩展性要求")
    ext = [
        ["NFR-032", "领域名称、术语表和预置包以配置和数据导入实现，程序不把某一领域写死在代码分支中", "高"],
        ["NFR-033", "模型、检索和导出通过适配接口接入。产品不包含未授权全文库和知识图谱", "高"],
    ]
    NFRS.extend(ext)
    add_table(doc, "表 4-6  可扩展性", ["编号", "要求"], [r[:2] for r in ext], [1600, 8038])
    h2(doc, "4.7 兼容性")
    para(doc, "最低交付客户端为 Web、Android 和微信小程序。Web 覆盖当前两个最新大版本的 Chrome 与 Edge，宽度 1280 像素时工作区本身不横向滚动。Android 支持 8.0 及以上。微信小程序承载普通用户路径；文件大小超过平台限制时，提示改用 Web 或 Android，不把该文件标为解析成功。iOS 可以复用同一接口，未交付不影响验收。管理后台只要求 Web。", indent=True)


def chapter5(doc):
    h1(doc, "5. 系统数据需求")
    h2(doc, "5.1 数据来源")
    bullets(doc, [
        "管理员导入的预置论文包及其来源类型、授权记录和导入人。",
        "用户上传的 PDF、手工补录的元数据和使用权确认记录。",
        "用户创建的项目、大纲、正文、润色确认和导出文件。",
        "系统生成的切片、向量、检索记录、分析结果、证据关联、引用核查和 Skill 执行记录。",
    ])
    h2(doc, "5.2 核心数据实体")
    para(doc, "下表给出必须保存的数据，不规定物理表名和字段类型。设计说明书可以把一个实体拆成多张表，但不得减少此处的信息。", indent=True)
    add_table(
        doc,
        "表 5-1  数据实体",
        ["实体", "必须包含的内容", "用途"],
        [
            ["User", "标识、登录名、邮箱、密码哈希、角色、状态", "身份与权限"],
            ["Project", "所有者、题目、论文类型、目标格式、领域、状态、时间", "论文项目"],
            ["Paper", "题名、作者、年份、摘要、DOI、来源类型、上传者或预置标记、是否已进入公用库、状态", "论文元数据"],
            ["DocumentFile", "存储键、哈希、大小、页数、上传人、使用权确认", "原始文件"],
            ["KnowledgeChunk", "论文、页码、顺序、原文、章节标记", "检索与证据"],
            ["Embedding", "切片标识、向量、模型标识", "语义检索"],
            ["RetrievalRecord", "项目、查询、过滤条件、返回切片、时间", "检索复现"],
            ["ResearchAnalysis", "项目、类型、所选论文、结果结构、时间", "分析保存"],
            ["Outline", "项目、版本号、章节树、确认状态、确认人与时间", "大纲"],
            ["DocumentContent", "项目、版本号、章节、段落、语言", "正文"],
            ["Citation", "项目、段落、论文、编号、L1/L2 结果", "正式引用"],
            ["Evidence", "切片、页码、原文、关联句子、支持程度", "证据链"],
            ["PolishRecord", "版本前后文本、档位、确认状态", "润色对照"],
            ["ExportTask", "格式、草稿或定稿、状态、文件键、错误", "导出"],
            ["AgentTask", "项目、意图、状态、步数、起止时间", "工作流"],
            ["SkillExecution", "任务、Skill、模型、输入摘要、结果、错误", "执行审计"],
            ["AuditLog", "操作者、动作、对象、时间、原因", "管理操作"],
        ],
        [1800, 4600, 3238],
    )
    h2(doc, "5.3 数据关联关系")
    bullets(doc, [
        "一个用户拥有多个项目，并可以贡献多篇进入公用知识库的论文。",
        "公用知识库同时包含预置论文和全部已索引的用户上传论文。",
        "一篇论文包含多个切片；一个切片对应所属模型的一条向量。",
        "一条证据指向一个切片，并可被多个引用句使用。",
        "正式引用指向一篇公用知识库中的论文，并至少在核验通过时指向一条证据。",
        "大纲版本、正文版本和润色记录都属于同一个项目。",
        "一次 Agent 任务包含多条 Skill 执行记录。",
    ])
    h2(doc, "5.4 数据生命周期")
    add_table(
        doc,
        "表 5-2  生命周期",
        ["对象", "过程", "删除后的可见性"],
        [
            ["上传论文", "上传、解析、进入公用库、检索、下线", "下线后所有用户检索不可见；历史引用标记来源已删除"],
            ["预置论文", "导入、进入公用库、下线、归档", "下线后不可检索；已有引用保留并提示下线"],
            ["项目", "创建、编辑、导出、删除", "项目列表消失；仅属于该项目的生成数据删除"],
            ["执行日志", "写入、按保留期归档", "默认保留 90 天，期限可配置"],
        ],
        [1800, 4200, 3638],
    )
    h2(doc, "5.5 数据约束")
    bullets(doc, [
        "标识在系统内唯一。论文文件以哈希辅助去重。",
        "文本使用 Unicode，能保存中英文和常用学术符号。",
        "时间保存到秒，并带统一时区，界面转换为用户本地时间。",
        "对外接口使用存储键或业务标识，不返回服务器本地绝对路径。",
        "向量维度和模型标识一起保存。更换嵌入模型后，旧向量不能与新向量混检，系统提示需要重建索引。",
    ])


def chapter6(doc):
    h1(doc, "6. AI 模型与智能体需求")
    h2(doc, "6.1 模型接入")
    bullets(doc, [
        "至少支持配置对话模型、嵌入模型。重排序模型和 OCR 服务可以留空。",
        "每个端点保存名称、调用地址、模型标识、超时和启用状态。密钥不明文回显。",
        "写作可以使用质量较高的对话模型；意图识别和格式整理可以使用更快的模型。具体型号写在设计说明书中。",
        "一次任务内记录实际使用的模型标识，便于复现实验。",
        "模型超时、鉴权失败和配额失败转换为第 9 章的 AI 异常，不把供应商原文堆给用户。",
    ])
    h2(doc, "6.2 Prompt 管理")
    bullets(doc, [
        "Literature、Analysis、Outline、Writing、Citation、Polish、Export 各自至少有一个启用版本。",
        "系统级约束包含：只使用给定证据、不编造文献、证据不足要明示、润色不改事实、建议与提取分开。",
        "领域术语表可配置，并进入分析和写作 Prompt。",
        "Prompt 变更保存版本号、时间、修改说明和是否启用。回滚即重新启用旧版本。",
        "启用写作和引用 Prompt 前，用第 10 章的引用样本做一次记录在案的检查。",
    ])
    h2(doc, "6.3 决策与执行")
    para(doc, "工作流是固定状态机，不是多角色自由对话。用户每条指令只产生一个任务。任务在人工节点结束当前自动执行。", indent=True)
    code_block(doc, "图 6-1  工作流状态", """
flowchart TD
    A[接收用户指令] --> B{能否识别意图}
    B -->|否| C[追问]
    B -->|是| D[检查前置状态]
    D -->|不满足| E[说明缺少大纲确认或索引]
    D -->|满足| F[调用对应 Skill]
    F --> G{输出是否通过结构校验}
    G -->|否| H[有限重试]
    H --> F
    G -->|是| I[写入结果]
    I --> J{是否人工节点}
    J -->|是| K[等待确认]
    J -->|否| L[任务完成]
""")
    add_table(
        doc,
        "表 6-1  意图与 Skill",
        ["意图", "前置条件", "Skill", "停止条件"],
        [
            ["整理研究主题", "用户提交主题", "S1", "返回合法结构化主题"],
            ["按关键词检索", "公用知识库存在已索引论文", "S2", "返回库内文献及来源"],
            ["解析 PDF", "文件已上传", "S3", "返回正文和章节"],
            ["多篇对比", "已选择 2～8 篇已索引论文", "S4", "保存带证据的对比"],
            ["方向分类", "已选择论文集合", "S5", "保存方向及依据论文"],
            ["研究空白", "已有研究现状或论文集合", "S6", "保存建议及依据"],
            ["大纲", "已填写研究目标", "S7", "等待作者确认"],
            ["章节写作", "大纲已确认", "S8", "写入带真实引用的草稿"],
            ["论文检查", "存在正文", "S9", "给出引用和逻辑问题"],
            ["导出", "用户要求 DOCX 或 PDF", "S10", "得到可打开文件；定稿先通过引用闸门"],
            ["润色", "存在正文选择范围", "润色", "等待作者确认"],
        ],
        [1600, 2800, 1800, 3438],
    )
    h2(doc, "6.4 AI 质量控制")
    bullets(doc, [
        "Skill 输出先做结构校验，缺字段时重试，仍失败则任务失败。",
        "S1～S10 先通过各自的独立测试，再接入工作流。工作流结果不能回写为 Skill 通过。",
        "写作输出中的每条正式引用都运行 L1 和 L2。",
        "支持程度为未找到证据时，去掉正式引用编号。",
        "同一任务不因为核查失败自动回到写作 Skill。",
        "大纲确认、润色确认和定稿导出的操作者与时间写入数据。",
    ])
    h2(doc, "6.5 AI 成本控制")
    bullets(doc, [
        "记录每次模型调用的任务、Skill、模型、输入与输出 token、耗时和结果。",
        "相同项目、相同查询和相同论文范围的检索结果可缓存，默认 7 天，论文重新索引后失效。",
        "每个用户每日生成类 token 上限可配置。达到上限后拒绝新的生成任务并说明原因，检索缓存仍可读取。",
        "单任务模型调用次数不超过步数上限。",
        "管理端可以按日查看 token 和失败次数，不展示正文。",
    ])


def chapter7(doc):
    h1(doc, "7. 系统接口需求")
    h2(doc, "7.1 接口约定")
    bullets(doc, [
        "业务接口前缀为 /api/v1。路径可以在接口说明书中调整，但本章列出的能力不能减少。",
        "除上传外，请求和响应使用 JSON。上传使用 multipart/form-data。",
        "列表接口支持 page、page_size、排序和模块约定的过滤字段。page_size 上限为 50。",
        "成功响应包含业务码、提示信息和数据。失败响应包含业务码、可展示提示和请求标识。",
        "需要登录的接口使用 Authorization 传递访问令牌。",
        "生成类接口可以同步返回小结果。超过 2 秒的解析、生成和导出返回任务标识，客户端通过任务查询接口轮询状态。",
    ])
    h2(doc, "7.2 业务接口清单")
    add_table(
        doc,
        "表 7-1  业务接口",
        ["模块", "方法", "路径", "说明", "需求"],
        [
            ["认证", "POST", "/api/v1/auth/register", "注册", "FR-001"],
            ["认证", "POST", "/api/v1/auth/login", "登录", "FR-002"],
            ["认证", "POST", "/api/v1/auth/logout", "退出", "FR-003"],
            ["用户", "GET/PATCH", "/api/v1/users/me", "当前用户资料", "FR-004"],
            ["项目", "GET/POST", "/api/v1/projects", "列表与创建", "FR-006、FR-009"],
            ["项目", "GET/PATCH/DELETE", "/api/v1/projects/{id}", "详情、修改、删除", "FR-007、FR-008"],
            ["知识库", "GET", "/api/v1/papers", "登录用户查看公用知识库", "FR-010、FR-028"],
            ["文件", "POST", "/api/v1/papers/upload", "上传并在索引后进入公用库", "FR-020、FR-030"],
            ["知识库", "DELETE", "/api/v1/papers/{id}", "上传者删除或管理员下线", "FR-029"],
            ["知识库", "POST", "/api/v1/admin/corpus", "导入预置包", "FR-031"],
            ["检索", "POST", "/api/v1/projects/{id}/retrievals", "混合检索", "FR-042"],
            ["问答", "POST", "/api/v1/projects/{id}/qa", "带证据问答", "FR-046"],
            ["分析", "POST", "/api/v1/projects/{id}/analyses", "单篇或多篇分析", "FR-060、FR-061"],
            ["大纲", "POST", "/api/v1/projects/{id}/outlines", "生成大纲", "FR-082"],
            ["大纲", "POST", "/api/v1/projects/{id}/outlines/{vid}/confirm", "确认大纲", "FR-085"],
            ["正文", "POST", "/api/v1/projects/{id}/sections/{sid}/drafts", "生成或修改章节", "FR-100"],
            ["正文", "PUT", "/api/v1/projects/{id}/document", "保存手动编辑", "FR-102"],
            ["润色", "POST", "/api/v1/projects/{id}/polishes", "生成润色对照", "FR-123"],
            ["润色", "POST", "/api/v1/projects/{id}/polishes/{pid}/confirm", "确认润色", "FR-125"],
            ["引用", "POST", "/api/v1/projects/{id}/citation-checks", "执行核查", "FR-143"],
            ["导出", "POST", "/api/v1/projects/{id}/exports", "创建导出任务", "FR-166"],
            ["任务", "GET", "/api/v1/agent-tasks/{id}", "查看步骤和错误", "FR-184"],
            ["版本", "POST", "/api/v1/projects/{id}/versions/{vid}/restore", "恢复历史版本", "FR-012"],
        ],
        [1100, 1500, 3900, 1838, 1300],
    )
    h2(doc, "7.3 模型与文件接口")
    bullets(doc, [
        "对话、嵌入、重排序和 OCR 通过服务端适配器调用。浏览器不持有模型密钥，也不直接提交供应商密钥。",
        "文档解析服务接收存储键，返回文本、元数据、页码和失败原因。",
        "文件存储接口按存储键读写。设计说明书可以选择本地磁盘；接口不把磁盘路径暴露给前端。",
        "DOI 元数据查询在文献带有 DOI 时调用。超时后按 FR-150 标记外部未核验。",
        "文档转换接口接收统一文档结构，返回 Markdown、DOCX、TEX 或 PDF 的存储键。",
    ])


def chapter8(doc):
    h1(doc, "8. 系统界面需求")
    para(doc, "Web 提供下表全部页面。Android 和微信小程序提供除管理后台以外的普通用户页面，信息可以上下排列。无权限时显示无权说明而不是空白。", indent=True)
    add_table(
        doc,
        "表 8-1  页面",
        ["页面", "路由", "必须呈现的内容"],
        [
            ["登录注册", "/login", "注册、登录、失败原因、系统用途的简短说明"],
            ["项目首页", "/", "本人项目列表、状态、新建入口"],
            ["项目工作台", "/projects/:id", "题目、状态、文献数、大纲状态、继续写作和最近任务"],
            ["公用知识库", "/library", "上传、进度、解析状态、上传者；索引后对登录用户可见"],
            ["文献检索", "/projects/:id/search", "查询、过滤、证据片段、原文定位"],
            ["文献分析", "/projects/:id/analysis", "单篇要素、对比矩阵、保存结果"],
            ["对话任务", "/projects/:id/chat", "自然语言指令、当前 Skill、追问和任务结果"],
            ["大纲编辑", "/projects/:id/outline", "章节树、写作意图、关联文献、确认按钮"],
            ["正文编辑", "/projects/:id/editor", "章节正文、手动编辑、生成、证据和支持程度"],
            ["润色", "/projects/:id/polish", "档位、对照、原因、确认和撤销"],
            ["引用管理", "/projects/:id/citations", "文献表、核查结果、问题句"],
            ["导出", "/projects/:id/export", "格式、草稿或定稿、任务状态、下载"],
            ["管理后台", "/admin", "用户状态、预置包、模型配置、配额和任务概况"],
        ],
        [1600, 2800, 5238],
    )
    bullets(doc, [
        "生成、解析和导出进行中时，按钮进入不可重复提交状态，并显示任务状态。",
        "证据片段与正文句子在同一屏幕可对照；窄窗口时允许分区上下排列。",
        "定稿导出被拒绝时，停留在导出页并列出未通过的句子链接。",
        "管理后台不作为普通用户导航项。",
    ])


def chapter9(doc):
    h1(doc, "9. 系统异常与边界处理")
    para(doc, "异常必须写入任务或文件状态，并向用户展示下表中的结果。系统不得在失败后把空文本标记为成功。", indent=True)
    h2(doc, "9.1 文档异常")
    add_table(doc, "表 9-1  文档异常", ["编号", "场景", "系统行为", "用户可见结果"], [
        ["EX-DOC-01", "PDF 损坏或加密", "标记解析失败，不建索引", "该文件失败，并说明无法读取"],
        ["EX-DOC-02", "扫描件置信度不足", "不进入已索引", "提示识别不完整，可改传文本型 PDF"],
        ["EX-DOC-03", "章节无法识别", "按页切分并标记", "论文仍可检索，显示章节未识别"],
        ["EX-DOC-04", "重复论文", "不新建索引", "指出已存在的论文"],
        ["EX-DOC-05", "格式或大小不符", "拒绝保存", "说明只接受 30 MB 以内 PDF"],
    ], [1400, 2200, 3019, 3019])
    h2(doc, "9.2 检索异常")
    add_table(doc, "表 9-2  检索异常", ["编号", "场景", "系统行为", "用户可见结果"], [
        ["EX-RET-01", "公用知识库没有已索引论文", "不调用对话模型", "提示先上传或等待入库"],
        ["EX-RET-02", "无相关切片", "返回空证据", "问答显示证据不足"],
        ["EX-RET-03", "过滤后无结果", "返回空列表", "提示放宽作者或年份条件"],
        ["EX-RET-04", "论文缺少年份或作者", "仍允许检索", "过滤条件不可用时显示元数据不完整"],
    ], [1400, 2200, 3019, 3019])
    h2(doc, "9.3 AI 执行异常")
    add_table(doc, "表 9-3  AI 异常", ["编号", "场景", "系统行为", "用户可见结果"], [
        ["EX-AI-01", "模型超时或不可用", "按重试上限执行，然后失败", "保留原内容，提示稍后重试"],
        ["EX-AI-02", "输出无法按契约解析", "有限重试，仍失败则终止", "不写入半截结构"],
        ["EX-AI-03", "任务步数超限", "终止任务", "显示已完成步骤和超限"],
        ["EX-AI-04", "Skill 失败", "记录错误，不调用后续依赖步骤", "指出失败 Skill"],
        ["EX-AI-05", "生成句没有证据", "去掉正式引用，标无证据草稿", "句子旁显示未找到证据"],
        ["EX-AI-06", "用户要求编造文献或降重", "拒绝该意图", "说明可改为检索或学术润色"],
        ["EX-AI-07", "达到每日 token 上限", "拒绝新的生成", "显示上限和恢复时间"],
    ], [1400, 2400, 2919, 2919])
    h2(doc, "9.4 导出异常")
    add_table(doc, "表 9-4  导出异常", ["编号", "场景", "系统行为", "用户可见结果"], [
        ["EX-EXP-01", "存在未通过 L1/L2 的正式引用", "拒绝定稿导出", "列出问题句，草稿导出仍可用"],
        ["EX-EXP-02", "转换器失败", "任务失败，不提供空文件", "显示失败阶段"],
        ["EX-EXP-03", "公式或图片不能排版", "写入占位和来源页码", "导出成功并提示有占位"],
        ["EX-EXP-04", "目录或编号生成失败", "Word 任务失败", "Markdown 若已成功则仍可下载"],
    ], [1400, 2800, 2719, 2719])


def chapter10(doc):
    h1(doc, "10. 测试与验收标准")
    h2(doc, "10.1 功能验收")
    para(doc, "第 3 章和第 4 章的全部需求通过，且没有未关闭的阻断缺陷，产品验收通过。", indent=True)
    rows = [
        ["AC-01", "注册、登录、退出和角色隔离", "FR-001～FR-005、NFR-015", "普通用户不能打开管理接口；错误密码不能登录"],
        ["AC-02", "项目创建、删除和版本恢复", "FR-006～FR-012", "删除项目后公用知识库中的论文仍在；版本可恢复"],
        ["AC-03", "PDF 上传进入公用库", "FR-020～FR-031", "用户 A 上传并索引后，用户 B 能检索到；损坏文件为解析失败；B 不能删除 A 的上传"],
        ["AC-04", "混合检索、过滤、证据不足", "FR-040～FR-051", "只返回公用知识库论文；无证据问题不出现确定性结论"],
        ["AC-05", "单篇提取与多篇矩阵", "FR-060、FR-061、FR-066", "缺失项为原文未识别或库内未找到"],
        ["AC-06", "大纲生成与确认闸门", "FR-080、FR-082～FR-085", "未确认时不能批量生成章节"],
        ["AC-07", "按节写作、手动保存、无证据标记", "FR-100～FR-104、FR-106", "库外文献不能留下正式编号"],
        ["AC-08", "润色对照、原意约束、拒绝降重", "FR-120、FR-123、FR-125～FR-128", "数字和引用在确认稿中保持；降重请求被拒绝"],
        ["AC-09", "引用 L1/L2 与 GB/T 7714", "FR-140～FR-147", "不一致元数据和无证据引用出现在核查报告"],
        ["AC-10", "Markdown、Word、草稿与定稿", "FR-160～FR-162、FR-166", "定稿在存在未通过引用时被拒绝"],
        ["AC-11", "工作流步数、重试和记录", "FR-180～FR-186", "超限任务终止；执行记录含 Skill 和错误"],
        ["AC-12", "文稿隔离与公用库", "NFR-016、NFR-017、NFR-019", "用户 A 不能读取用户 B 的大纲和正文；A 能检索 B 已索引的上传论文"],
        ["AC-13", "S1～S10 独立测试", "FR-187、FR-188", "十个 Skill 各有独立通过记录；工作流通过不能代替其中任何一条"],
        ["AC-14", "Web、Android、微信小程序", "第 4.7 节、第 8 章", "三端都能完成主题、检索、上传解析、对比、大纲、带引用正文、检查和可打开的 DOCX/PDF。未交付 iOS 仍可通过"],
    ]
    ACS.extend(rows)
    add_table(doc, "表 10-1  功能验收", ["验收编号", "验收内容", "覆盖需求", "通过标准"],
              rows, [1100, 2800, 2938, 2800])
    h2(doc, "10.2 RAG 质量测试")
    para(doc, "使用部署配置中的领域包，编制不少于 30 条标注问题。每条标明相关论文。指标若因领域包调整而修订，写入文档新版本。", indent=True)
    add_table(doc, "表 10-2  RAG 指标", ["指标", "验收目标", "口径"], [
        ["Recall@5", "不低于 0.70", "前 5 条切片所属论文覆盖标注相关论文的比例，对 30 条问题取平均"],
        ["证据定位", "抽检 20 条全部可打开页码", "从检索结果打开的片段与 PDF 对应页一致"],
        ["范围正确性", "抽检 20 次均为 0 条越界", "结果论文都属于公用知识库，且不包含他人项目正文"],
        ["拒答", "抽检 10 条无证据问题全部拒答", "不出现确定性结论和正式引用"],
    ], [1800, 2800, 5038])
    h2(doc, "10.3 AI 生成质量测试")
    add_table(doc, "表 10-3  生成质量", ["指标", "通过标准", "样本"], [
        ["引用可回链率", "定稿导出中的正式引用为 100%", "至少 2 篇样例论文的定稿"],
        ["库外正式引用", "为 0", "写作测试中模型若输出库外文献，系统结果仍为 0"],
        ["证据覆盖", "正式引用句 100% 有证据片段", "同一定稿样本"],
        ["润色忠实", "抽检句的数字和引用与原文一致", "每档润色至少 10 句"],
        ["建议标记", "研究不足和创新点均带建议标记", "至少 5 条输出"],
    ], [1800, 4200, 3638])
    h2(doc, "10.4 性能与安全测试")
    bullets(doc, [
        "按表 4-2 在记录硬件、数据量和模型标识的条件下各测量不少于 20 次，报告 P95。",
        "用 10 个会话和 3 个排队生成任务做并发测试，系统保持可登录、可查询状态。",
        "用另一用户的项目标识、文件标识和导出标识访问，期望全部拒绝。",
        "达到 token 上限后，新的生成请求被拒绝，已保存正文仍可读取。",
        "检查仓库和前端包，确认不存在模型密钥和数据库口令。",
    ])
    h2(doc, "10.5 验收用例内容")
    para(doc, "每条功能需求在测试用例中包含功能描述、输入、操作、期望输出、异常输入和期望异常结果。用例编号回指 FR、NFR 或 EX。", indent=True)
    h2(doc, "10.6 验收流程")
    code_block(doc, "图 10-1  验收流程", """
flowchart TD
    A[管理员导入预置论文] --> B[用户登录并创建项目]
    B --> C[上传一篇 PDF 并进入公用知识库]
    C --> D[等待状态变为已索引]
    D --> E[检索并打开证据页码]
    E --> F[生成两篇论文的对比矩阵]
    F --> G[生成大纲并确认]
    G --> H[生成一节草稿并查看支持程度]
    H --> I[润色对照并确认]
    I --> J[引用核查]
    J --> K[导出 Markdown、Word、LaTeX 和 PDF]
    K --> L[在引用未通过时尝试定稿并确认被拒绝]
    L --> M[修正后完成一次定稿导出]
""")


def chapter11(doc):
    h1(doc, "11. 实现约定")
    para(doc, "实现可以按依赖顺序推进。后做的功能仍是本产品的组成部分，验收时必须存在。默认目录、技术栈和日常开发约束写在仓库根目录 AGENTS.md。本文只规定可观察行为。", indent=True)
    add_table(doc, "表 11-1  建议实现顺序", ["顺序", "先完成的能力", "依赖"], [
        ["1", "S1 主题结构化，S3 上传、解析和章节", "部署配置 CFG-01～CFG-03"],
        ["2", "S2 混合检索、重排序和真实文献来源", "已索引论文"],
        ["3", "S4 对比、S5 方向分类、S6 研究空白、S7 大纲", "检索"],
        ["4", "S8 带真实引用的章节，S9 引用和逻辑检查", "已确认大纲"],
        ["5", "S10 可打开的 DOCX 与 PDF；润色对照同时完成", "正文"],
        ["6", "S1～S10 独立测试、管理端、配额和审计", "主路径可用"],
        ["7", "Android 与微信小程序走通 S1～S10", "Web 主路径和独立测试已通过"],
    ], [1200, 5200, 3238])
    h2(doc, "11.1 交付物")
    bullets(doc, [
        "需求规格说明书（本文）。",
        "AGENTS.md，作为开发过程中的实现参考。",
        "系统架构设计说明书、数据库设计说明和 API 接口说明书。",
        "界面原型。",
        "Skill 输入输出说明，内容与附录 B 一致。",
        "测试用例、不少于 30 条标注题、测试报告和缺陷列表。",
        "部署说明、用户使用说明和可运行的完整系统。",
    ])
    h2(doc, "11.2 需求变更")
    para(doc, "变更产品范围、验收指标或项目题目时，升版本文并保留旧版，同时同步 AGENTS.md 中受影响的规则。", indent=True)


def chapter12(doc):
    h1(doc, "12. 风险与处理")
    add_table(doc, "表 12-1  风险", ["风险", "影响", "处理"], [
        ["PDF 版式复杂", "解析文本残缺，检索和页码不准", "文本型 PDF 作为验收样例；解析失败可见。扫描件低于置信阈值时不得标为已索引，且不计入 NFR-012 时限"],
        ["检索命中不足", "问答经常证据不足", "调整切片和混合权重，并用 30 条标注题复测"],
        ["模型补写文献", "产生不存在的引用", "正式引用只接受库内标识；定稿执行 L1/L2"],
        ["工作流来回调用", "费用上升且任务不结束", "步数、重试和禁止核查失败后自动重写"],
        ["预置论文版权不清", "数据不能合法使用", "没有 CFG-02 记录的文件不得导入"],
        ["正文发送到外部模型", "未发表内容超出用户预期", "首次确认数据处理说明；日志不记全文"],
        ["API 费用超支", "生成服务不可用", "缓存、按节生成、每日 token 上限"],
        ["领域与预置包不符", "系统对用户主题无证据", "只装载 CFG-01 指定的一个研究领域"],
    ], [2200, 3219, 4219])
    para(doc, "作者确认和引用闸门属于产品规则。降低查重率或规避相似性检测不属于本产品。", indent=True)


def appendix(doc):
    h1(doc, "附录 A  用例与流程索引")
    para(doc, "业务场景 UC-01～UC-07 见第 2.4 节。主流程见图 2-1，工作流见图 6-1，验收流程见图 10-1。下表用于从用例追踪到验收。", indent=True)
    add_table(doc, "表 A-1  用例追踪", ["用例", "验收", "结果"], [
        ["UC-01", "AC-03", "上传论文进入公用知识库后可被其他用户检索"],
        ["UC-02", "AC-04", "证据可定位或明确不足"],
        ["UC-03", "AC-05", "矩阵空缺有固定填法"],
        ["UC-04", "AC-06", "大纲可确认"],
        ["UC-05", "AC-07", "章节草稿带证据状态"],
        ["UC-06", "AC-08、AC-09", "润色可确认，引用可核查"],
        ["UC-07", "AC-10", "草稿可导出，未通过引用不能定稿"],
    ], [1800, 2500, 5338])

    h1(doc, "附录 B  Skill 输入输出契约")
    para(doc, "契约规定字段和失败语义。Prompt 正文放在 Prompt 版本库，不写进本文。", indent=True)
    skills = [
        ("S1 主题结构化", "研究主题文本",
         "主题名称、研究对象、关键词、问题边界",
         "无法形成合法结构时失败，不返回无字段散文"),
        ("S2 文献检索", "中文或英文关键词",
         "公用知识库中的真实文献及来源：标识、题名、作者、年份",
         "公用库没有已索引论文时不生成文献"),
        ("S3 论文解析", "PDF 存储键",
         "正文和章节树；验收样例必须识别章节",
         "损坏、加密或低置信扫描件记解析失败"),
        ("S4 多篇对比", "2～8 篇已索引论文",
         "带证据的对比结果；空缺为库内未找到",
         "论文未索引时拒绝该篇"),
        ("S5 方向分类", "论文集合",
         "研究方向及每一类的依据论文",
         "集合为空时不生成分类"),
        ("S6 研究空白", "研究现状或论文集合",
         "候选空白、依据或证据不足标记，类型为建议",
         "没有输入材料时不生成空白"),
        ("S7 大纲", "研究目标",
         "可编辑的章节树和每节写作意图",
         "缺研究目标时不生成"),
        ("S8 章节写作", "章节要求、已确认大纲、证据标识",
         "正文及可回链的真实引用",
         "大纲未确认且要求批量生成时拒绝"),
        ("S9 论文检查", "完整论文项目",
         "引用问题清单和逻辑问题清单",
         "正文为空时返回空报告"),
        ("S10 文档导出", "论文项目",
         "可打开的 DOCX 和 PDF",
         "定稿未通过引用闸门时返回 EX-EXP-01；空文件不算成功"),
        ("润色", "选区文本、档位、术语表",
         "对照文本、修改原因、是否拒绝",
         "降重或规避检测请求被拒绝，原文不变"),
    ]
    add_table(doc, "表 B-1  Skill 契约", ["Skill", "输入", "输出", "失败"],
              [s for s in skills], [1400, 2800, 3019, 2419])

    h1(doc, "附录 C  需求追踪")
    para(doc, "编号段与模块的对应关系如下。详细条目见各章表格。", indent=True)
    add_table(doc, "表 C-1  编号段", ["编号段", "模块", "验收重点"], [
        ["FR-001～FR-012", "用户与项目", "AC-01、AC-02"],
        ["FR-020～FR-031", "知识库", "AC-03"],
        ["FR-040～FR-051", "RAG 检索与溯源", "AC-04"],
        ["FR-060～FR-066", "文献分析", "AC-05"],
        ["FR-080～FR-085", "大纲", "AC-06"],
        ["FR-100～FR-106", "正文写作", "AC-07"],
        ["FR-120～FR-128", "润色", "AC-08"],
        ["FR-140～FR-150", "引用", "AC-09"],
        ["FR-160～FR-167", "导出", "AC-10"],
        ["FR-180～FR-188", "工作流与 S1～S10", "AC-11、AC-13、AC-14"],
        ["NFR-001～NFR-033", "非功能", "AC-12 及第 10.2～10.4 节"],
        ["EX-DOC/RET/AI/EXP", "异常", "对应功能用例的异常输入"],
    ], [2400, 2800, 4438])
    para(doc, f"功能需求共 {len(FRS)} 条，非功能需求共 {len(NFRS)} 条。全部纳入产品验收。", indent=True)
    add_table(doc, "表 C-2  功能需求索引", ["编号", "需求"],
              [[a, b] for a, b, _c, _d in FRS], [1800, 7838])

    h1(doc, "附录 D  参考资料")
    bullets(doc, [
        "ISO/IEC/IEEE 29148:2018 Systems and software engineering — Life cycle processes — Requirements engineering。",
        "IEEE Std 830-1998 IEEE Recommended Practice for Software Requirements Specifications。本文借用其需求可追踪、可验证的写法，章节按本项目重组。",
        "GB/T 7714 信息与文献 参考文献著录规则。本产品的默认参考文献格式。",
        "仓库根目录 AGENTS.md：开发过程中的实现参考。",
        "项目题目：" + TITLE + "。",
    ])
    para(doc, "— 本文结束 —", center=True, before=12)


if __name__ == "__main__":
    build()
