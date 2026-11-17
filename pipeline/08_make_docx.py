# -*- coding: utf-8 -*-
"""把 Markdown 设计报告转换为排版良好的 DOCX（封面/目录/页眉页脚/表格/图片）。"""
import re, shutil
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FIG = DOCS / "figures"
MD = DOCS / "设计报告.md"
OUT = DOCS / "设计报告.docx"
SYS = ROOT / "system"

NAVY = RGBColor(0x0B, 0x3B, 0x5A)
TEAL = RGBColor(0x17, 0x7E, 0x89)
GRAY = RGBColor(0x5A, 0x6B, 0x7A)
LIGHT = RGBColor(0x7F, 0x9B, 0xB5)
BODY_FONT = "宋体"
HEAD_FONT = "微软雅黑"


def set_cn_font(run, name, size=None, bold=None, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def para_border(p, color="1F6F8B", size=6, position="bottom"):
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    el = OxmlElement(f"w:{position}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:space"), "4")
    el.set(qn("w:color"), color)
    pbdr.append(el)
    pPr.append(pbdr)


def add_field(paragraph, instr, placeholder=""):
    run = paragraph.add_run()
    fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = placeholder
    fld3 = OxmlElement("w:fldChar"); fld3.set(qn("w:fldCharType"), "end")
    run._r.append(fld1); run._r.append(it); run._r.append(fld2); run._r.append(t); run._r.append(fld3)


def enable_update_fields(doc):
    settings = doc.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    settings.append(uf)


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = "PAGE"
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "1"
    fld3 = OxmlElement("w:fldChar"); fld3.set(qn("w:fldCharType"), "end")
    run._r.append(fld1); run._r.append(it); run._r.append(fld2); run._r.append(t); run._r.append(fld3)


def setup_styles(doc):
    st = doc.styles["Normal"]
    st.font.name = BODY_FONT
    st.font.size = Pt(10.5)
    st._element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    pf = st.paragraph_format
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(4)

    for name, size, color, before, after in [("Heading 1", 20, NAVY, 0, 14), ("Heading 2", 16, NAVY, 14, 8), ("Heading 3", 12.5, TEAL, 10, 4)]:
        s = doc.styles[name]
        s.font.name = HEAD_FONT
        s._element.rPr.rFonts.set(qn("w:eastAsia"), HEAD_FONT)
        s.font.size = Pt(size)
        s.font.bold = True
        s.font.color.rgb = color
        s.paragraph_format.space_before = Pt(before)
        s.paragraph_format.space_after = Pt(after)
        s.paragraph_format.keep_with_next = True
        s.paragraph_format.line_spacing = 1.2


def setup_page(doc):
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.4)
    sec.bottom_margin = Cm(2.2)
    sec.left_margin = Cm(2.6)
    sec.right_margin = Cm(2.4)
    sec.header_distance = Cm(1.2)
    sec.footer_distance = Cm(1.2)

    sec.different_first_page_header_footer = True
    # 页眉
    hp = sec.header.paragraphs[0]
    hp.text = ""
    hp.paragraph_format.tab_stops.add_tab_stop(Cm(15.5), WD_TAB_ALIGNMENT.RIGHT)
    r = hp.add_run("城市积水风险智慧预警系统设计报告")
    set_cn_font(r, HEAD_FONT, 8.5, False, GRAY)
    hp.add_run("\t")
    r = hp.add_run("第 4 小组")
    set_cn_font(r, HEAD_FONT, 8.5, False, GRAY)
    para_border(hp, "B9C9D6", 4)

    # 页脚
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("— ")
    set_cn_font(r, BODY_FONT, 8.5, False, GRAY)
    add_page_number(fp)
    r = fp.add_run(" —")
    set_cn_font(r, BODY_FONT, 8.5, False, GRAY)


def add_cover(doc, title, subtitle):
    for _ in range(1):
        doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run("《智慧城市》课程结课设计")
    set_cn_font(r, HEAD_FONT, 12, True, TEAL)
    p.paragraph_format.space_after = Pt(10)

    p = doc.add_paragraph()
    r = p.add_run(title)
    set_cn_font(r, HEAD_FONT, 24, True, NAVY)
    p.paragraph_format.line_spacing = 1.2

    p = doc.add_paragraph()
    r = p.add_run(subtitle)
    set_cn_font(r, HEAD_FONT, 12.5, False, GRAY)
    p.paragraph_format.space_after = Pt(16)
    para_border(p, "1F6F8B", 8)

    # 封面主图
    cover = FIG / "shot_50.png"
    if cover.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(cover), width=Cm(14.6))
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cap.add_run("福田数字孪生 · 50 年一遇情景 T+06:40")
        set_cn_font(r, HEAD_FONT, 8.5, False, LIGHT)

    doc.add_paragraph()
    info = [
        ("课程名称", "智慧城市"),
        ("设计题目", "城市积水风险智慧预警系统"),
        ("小组", "第 4 小组"),
        ("小组成员", "________（队长）  ________  ________  ________"),
        ("指导教师", "________"),
        ("完成日期", "2026 年 11 月"),
    ]
    table = doc.add_table(rows=len(info), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Cm(4.0)
    table.columns[1].width = Cm(10.5)
    for i, (k, v) in enumerate(info):
        c0, c1 = table.cell(i, 0), table.cell(i, 1)
        c0.width = Cm(4.0); c1.width = Cm(10.5)
        p0 = c0.paragraphs[0]; p0.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = p0.add_run(k)
        set_cn_font(r, HEAD_FONT, 9, True, NAVY)
        p1 = c1.paragraphs[0]
        r = p1.add_run(v)
        set_cn_font(r, BODY_FONT, 9, False, RGBColor(0x33, 0x33, 0x33))
    doc.add_page_break()


def add_static_toc(doc, entries, pages=None):
    p = doc.add_paragraph()
    r = p.add_run("目  录")
    set_cn_font(r, HEAD_FONT, 20, True, NAVY)
    p.paragraph_format.space_after = Pt(12)
    pages = pages or {}
    for level, text in entries:
        para = doc.add_paragraph()
        pf = para.paragraph_format
        pf.tab_stops.add_tab_stop(Cm(15.6), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        pf.space_before = Pt(4 if level == 1 else 0)
        pf.space_after = Pt(1)
        pf.line_spacing = 1.15
        if level == 2:
            pf.left_indent = Cm(0.8)
        r = para.add_run(text)
        set_cn_font(r, HEAD_FONT if level == 1 else BODY_FONT, 11.5 if level == 1 else 9.2,
                    level == 1, NAVY if level == 1 else RGBColor(0x33, 0x44, 0x55))
        r = para.add_run("\t" + str(pages.get(text, "—")))
        set_cn_font(r, BODY_FONT, 11 if level == 1 else 9, level == 1,
                    NAVY if level == 1 else GRAY)
    doc.add_page_break()


def collect_headings(lines):
    out = []
    in_code = False
    for line in lines:
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith("## "):
            out.append((1, line[3:].strip()))
        elif line.startswith("### "):
            out.append((2, line[4:].strip()))
    return out


def add_inline(p, text, size=10.5, color=None, italic=False):
    # 去掉链接，保留文字
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    tokens = re.split(r"(\*\*.+?\*\*|`.+?`)", text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            r = p.add_run(tok[2:-2])
            set_cn_font(r, HEAD_FONT, size, True, color)
        elif tok.startswith("`") and tok.endswith("`"):
            r = p.add_run(tok[1:-1])
            set_cn_font(r, "Consolas", size - 1, False, RGBColor(0x0B, 0x5A, 0x72))
        else:
            r = p.add_run(tok)
            set_cn_font(r, BODY_FONT, size, False, color)
            if italic:
                r.font.italic = True


def add_body_para(doc, text, indent=True, size=10.5, color=None, italic=False, align_justify=True):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    if indent:
        pf.first_line_indent = Cm(0.74)
    pf.space_after = Pt(4)
    if align_justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_inline(p, text, size=size, color=color, italic=italic)
    return p


def add_table(doc, rows):
    if not rows:
        return
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    table = doc.add_table(rows=len(rows), cols=ncol)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.allow_autofit = False
    # 按内容长度分配列宽，避免“来源”列被压成两三个字
    weights = []
    for j in range(ncol):
        mx = max(len(re.sub(r"[*`]", "", r[j])) for r in rows)
        weights.append(min(22, max(4, mx)))
    total = sum(weights)
    widths = [max(1.8, 16.0 * w / total) for w in weights]
    scale = 16.0 / sum(widths)
    widths = [w * scale for w in widths]
    for j, w in enumerate(widths):
        table.columns[j].width = Cm(w)
    # 表头
    for j, txt in enumerate(rows[0]):
        cell = table.cell(0, j)
        cell.width = Cm(widths[j])
        shade(cell, "0B3B5A")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(re.sub(r"\*\*", "", txt))
        set_cn_font(r, HEAD_FONT, 8.4, True, RGBColor(0xFF, 0xFF, 0xFF))
    # 表体
    for i, row in enumerate(rows[1:], start=1):
        for j, txt in enumerate(row):
            cell = table.cell(i, j)
            cell.width = Cm(widths[j])
            if i % 2 == 0:
                shade(cell, "EEF4F8")
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.15
            add_inline(p, txt, size=8.4, color=RGBColor(0x22, 0x33, 0x44))
    # 表头重复
    tr = table.rows[0]._tr
    trPr = tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_image(doc, alt, src):
    path = (DOCS / src).resolve()
    if not path.exists():
        print("缺少图片", path)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    try:
        from PIL import Image
        im = Image.open(path)
        w, h = im.size
        width = Cm(16.2) if w / h > 1.35 else Cm(12.5)
        if "fig_maxdepth" in path.name:
            width = Cm(14.2)
    except Exception:
        width = Cm(15.5)
    p.add_run().add_picture(str(path), width=width)
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(alt)
    set_cn_font(r, HEAD_FONT, 8.6, False, GRAY)
    cap.paragraph_format.space_after = Pt(8)


def add_code(doc, code):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "F2F5F8")
    pPr.append(shd)
    p.paragraph_format.left_indent = Cm(0.4)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    for i, line in enumerate(code.rstrip("\n").split("\n")):
        r = p.add_run(line)
        set_cn_font(r, "Consolas", 8.2, False, RGBColor(0x1B, 0x3A, 0x4A))
        if i < len(code.rstrip("\n").split("\n")) - 1:
            r.add_break()


def build():
    text = MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    # 标题/副标题
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "城市积水风险智慧预警系统设计报告")
    subtitle = next((l[3:].strip() for l in lines if l.startswith("## ——")), "")
    # 正文起点：## 摘要
    start = next(i for i, l in enumerate(lines) if l.startswith("## 摘要"))
    body = lines[start:]

    doc = Document()
    setup_styles(doc)
    setup_page(doc)
    enable_update_fields(doc)
    add_cover(doc, title, subtitle)
    import json as _json
    toc_pages = {}
    tp = DOCS / "toc_pages.json"
    if tp.exists():
        toc_pages = _json.loads(tp.read_text(encoding="utf-8"))
    add_static_toc(doc, collect_headings(body), toc_pages)

    i = 0
    first_h2 = True
    while i < len(body):
        line = body[i].rstrip()
        if not line.strip():
            i += 1; continue
        if line.startswith("## "):
            if not first_h2:
                doc.add_page_break()
            first_h2 = False
            h = doc.add_heading(level=1)
            r = h.add_run(line[3:].strip())
            set_cn_font(r, HEAD_FONT, 19, True, NAVY)
            para_border(h, "1F6F8B", 8)
            i += 1; continue
        if line.startswith("### "):
            h = doc.add_heading(level=2)
            r = h.add_run(line[4:].strip())
            set_cn_font(r, HEAD_FONT, 14, True, TEAL)
            i += 1; continue
        if line.startswith("#### "):
            h = doc.add_heading(level=3)
            r = h.add_run(line[5:].strip())
            set_cn_font(r, HEAD_FONT, 11.5, True, NAVY)
            i += 1; continue
        if line.startswith("```"):
            code = []
            i += 1
            while i < len(body) and not body[i].startswith("```"):
                code.append(body[i]); i += 1
            i += 1
            add_code(doc, "\n".join(code))
            continue
        if line.startswith("!["):
            m = re.match(r"!\[(.*?)\]\((.*?)\)", line)
            if m:
                add_image(doc, m.group(1), m.group(2))
            i += 1; continue
        if line.startswith("|"):
            rows = []
            while i < len(body) and body[i].strip().startswith("|"):
                raw = body[i].strip().strip("|")
                cells = [c.strip() for c in raw.split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            add_table(doc, rows)
            continue
        if line.strip() == "---":
            i += 1; continue
        if line.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.space_after = Pt(6)
            pPr = p._p.get_or_add_pPr()
            shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "EEF6FA")
            pPr.append(shd)
            add_inline(p, line[2:].strip(), size=9.5, color=GRAY, italic=True)
            i += 1; continue
        if re.match(r"^\d+\.\s+", line):
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.space_after = Pt(3)
            add_inline(p, re.sub(r"^\d+\.\s+", "", line))
            i += 1; continue
        if line.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(3)
            add_inline(p, line[2:])
            i += 1; continue
        # 普通段落
        add_body_para(doc, line.strip())
        i += 1

    doc.core_properties.title = title
    doc.core_properties.subject = "智慧城市课程结课设计"
    doc.core_properties.author = "第 4 小组"
    doc.save(OUT)
    print("保存", OUT, OUT.stat().st_size / 1e6, "MB")


if __name__ == "__main__":
    # 把系统最新截图复制到报告图目录
    FIG.mkdir(parents=True, exist_ok=True)
    for src, dst in [("shot_replay.png", "shot_replay.png"), ("shot_50b.png", "shot_50.png"),
                     ("shot_sensor.png", "shot_sensor.png")]:
        p = SYS / src
        if p.exists():
            shutil.copy(p, FIG / dst)
    build()
