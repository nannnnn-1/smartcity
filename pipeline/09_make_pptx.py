# -*- coding: utf-8 -*-
"""生成答辩 PPT（16:9，深空蓝数字孪生风格）。"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "docs" / "figures"
OUT = ROOT / "docs" / "答辩PPT.pptx"

W, H = 13.333, 7.5
BG = RGBColor(0x06, 0x11, 0x1F)
PANEL = RGBColor(0x0B, 0x1B, 0x2C)
CYAN = RGBColor(0x5F, 0xD7, 0xFF)
TEAL = RGBColor(0x35, 0xD0, 0xA5)
AMBER = RGBColor(0xFF, 0xC1, 0x5E)
RED = RGBColor(0xFF, 0x4D, 0x5E)
PURPLE = RGBColor(0xC7, 0x7D, 0xFF)
TEXT = RGBColor(0xE8, 0xF6, 0xFF)
MUTED = RGBColor(0x7F, 0x9B, 0xB5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
HEAD = "微软雅黑"
NUM = "Bahnschrift"


def solid(shape, color, alpha=None):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    if alpha is not None:
        srgb = shape.fill.fore_color._xFill
        # 通过 XML 设置透明度
        for el in shape.fill._xPr.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr'):
            a = etree.SubElement(el, '{http://schemas.openxmlformats.org/drawingml/2006/main}alpha')
            a.set('val', str(int(alpha * 100000)))


def rect(slide, x, y, w, h, color=PANEL, alpha=None, line=None, lw=0.8):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.shadow.inherit = False
    solid(shp, color, alpha)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(lw)
    return shp


def text(slide, x, y, w, h, s, size=14, color=TEXT, bold=False, font=HEAD,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.15, spacing=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = line_spacing
    if spacing:
        p.space_after = Pt(spacing)
    r = p.add_run()
    r.text = s
    r.font.name = font
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return box


def multi(slide, x, y, w, h, lines, size=12, color=TEXT, bullet=False, space=4, line_spacing=1.2):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    for i, item in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = line_spacing
        p.space_after = Pt(space)
        if bullet:
            p.level = 0
            pPr = p._p.get_or_add_pPr()
            bu = etree.SubElement(pPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}buChar')
            bu.set('char', '•')
        r = p.add_run(); r.text = item
        r.font.name = HEAD; r.font.size = Pt(size); r.font.color.rgb = color
    return box


def pic_fit(slide, path, x, y, w, h, border=True):
    """按容器比例裁剪图片，避免拉伸。"""
    path = Path(path)
    if not path.exists():
        return
    iw, ih = Image.open(path).size
    target = w / h
    src = iw / ih
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    if src > target:
        crop = (1 - target / src) / 2
        pic.crop_left = crop; pic.crop_right = crop
    else:
        crop = (1 - src / target) / 2
        pic.crop_top = crop; pic.crop_bottom = crop
    if border:
        pic.line.color.rgb = RGBColor(0x1F, 0x4A, 0x66)
        pic.line.width = Pt(0.8)
    return pic


def header(slide, kicker, title, sub=None, page=None):
    rect(slide, 0, 0, W, 0.06, CYAN)
    text(slide, 0.62, 0.42, 7.8, 0.3, kicker.upper(), size=9.5, color=CYAN, font=NUM, bold=True)
    text(slide, 0.62, 0.70, 11.6, 0.62, title, size=27, color=TEXT, bold=True)
    if sub:
        text(slide, 0.64, 1.34, 11.8, 0.42, sub, size=11.5, color=MUTED)
    rect(slide, 0.62, 1.26 if not sub else 1.82, 0.85, 0.035, TEAL)
    if page is not None:
        text(slide, 12.15, 7.08, 0.6, 0.25, f"{page:02d}", size=9, color=MUTED, font=NUM, align=PP_ALIGN.RIGHT)


def chip(slide, x, y, w, s, color=CYAN, size=9.5):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.30))
    shp.adjustments[0] = 0.22
    solid(shp, color, 0.12)
    shp.line.color.rgb = color; shp.line.width = Pt(0.6)
    tf = shp.text_frame; tf.word_wrap = False
    tf.margin_left = Inches(0.08); tf.margin_right = Inches(0.05)
    tf.margin_top = 0; tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = s; r.font.name = HEAD; r.font.size = Pt(size); r.font.color.rgb = color


def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s


def bg(slide):
    rect(slide, 0, 0, W, H, BG)
    # 细微网格
    for x in [2.2, 4.4, 6.6, 8.8, 11.0]:
        ln = slide.shapes.add_connector(1, Inches(x), Inches(0), Inches(x), Inches(H))
        ln.line.color.rgb = RGBColor(0x0D, 0x25, 0x38); ln.line.width = Pt(0.4)


def slide1(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    pic_fit(s, FIG / "shot_replay.png", 4.6, 0, 8.8, 7.5, border=False)
    rect(s, 0, 0, 8.0, H, BG, alpha=0.90)
    rect(s, 0, 0, W, 0.08, CYAN)
    rect(s, 7.98, 0, 0.02, H, CYAN, alpha=0.45)
    text(s, 0.8, 0.8, 4.5, 0.3, "《智慧城市》课程结课设计", size=11, color=TEAL, bold=True)
    text(s, 0.78, 1.55, 5.0, 1.7, "深澜", size=64, color=TEXT, bold=True)
    text(s, 0.82, 2.85, 5.0, 0.5, "城市积水风险智慧预警平台", size=18, color=WHITE, bold=True)
    text(s, 0.82, 3.36, 4.6, 0.6, "深圳福田数字孪生 · 数据驱动的三维推演", size=11, color=MUTED)
    rect(s, 0.82, 4.12, 1.6, 0.035, TEAL)
    text(s, 0.82, 4.36, 4.2, 0.9, "2023·9·7 复盘  /  50 年一遇  /  5 年一遇", size=11, color=CYAN, font=NUM)
    text(s, 0.82, 5.05, 4.2, 0.4, "第 4 小组  ·  2026 年 11 月", size=11, color=MUTED)
    text(s, 0.82, 6.55, 4.4, 0.3, "SHENLAN  ·  URBAN FLOOD DIGITAL TWIN", size=8, color=RGBColor(0x3F, 0x6A, 0x86), font=NUM)
    notes(s, "开场：各位老师好，我们是第4小组。我们的题目是城市积水风险智慧预警系统。先用一句话概括：把福田26.7平方公里的地形、建筑、降雨和预警规则装进一个可交互的三维数字孪生里，回答水在哪里、有多深、该去哪里处置。")
    return s


def slide2(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "MOTIVATION", "一场雨，暴露了三个缺口", "2023 年 9 月 7—8 日，深圳有记录以来最强特大暴雨", 2)
    stats = [("202.8", "mm", "全市平均雨量"), ("263.8", "mm", "福田区平均雨量"), ("116.8", "mm/h", "最大 1 小时雨量"), ("7", "项", "滑动雨量破纪录")]
    for i, (v, u, lab) in enumerate(stats):
        x = 0.65 + i * 3.12
        rect(s, x, 2.02, 2.86, 1.28, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
        text(s, x + 0.18, 2.12, 1.8, 0.6, v, size=30, color=CYAN if i < 3 else AMBER, font=NUM, bold=True)
        text(s, x + 0.18 + (0.52 if len(v) <= 3 else 1.50), 2.42, 0.8, 0.3, u, size=9, color=MUTED)
        text(s, x + 0.18, 2.88, 2.5, 0.3, lab, size=10, color=MUTED)
    gaps = [
        ("表达维度不足", "二维地图与列表，难以呈现“水深—建筑—路网—地下空间”的空间关系"),
        ("推演能力不足", "监测是“已经发生”，防汛需要“未来 1—6 小时可能发生”"),
        ("数据门槛高", "逐点易涝点、管网拓扑、风险分区均未公开，真实耦合难以落地"),
    ]
    for i, (t, d) in enumerate(gaps):
        x = 0.65 + i * 4.18
        rect(s, x, 3.65, 3.92, 2.15, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
        rect(s, x, 3.65, 0.05, 2.15, [RED, AMBER, PURPLE][i])
        text(s, x + 0.2, 3.82, 3.5, 0.35, f"0{i+1}", size=12, color=[RED, AMBER, PURPLE][i], font=NUM, bold=True)
        text(s, x + 0.2, 4.16, 3.5, 0.4, t, size=15, color=TEXT, bold=True)
        text(s, x + 0.2, 4.62, 3.45, 0.9, d, size=10.5, color=MUTED, line_spacing=1.35)
    text(s, 0.65, 6.18, 12, 0.5, "我们的选择：数据先行，用公开数据把“地形—建筑—降雨—阈值”主链打通，再做可解释的推演与三维表达。", size=12.5, color=TEAL, bold=True)
    notes(s, "9·7暴雨，福田平均263.8毫米，最大一小时116.8毫米，7项纪录。更关键的是它超过了100年一遇设计标准，说明只靠阈值报警不够。我们总结三个缺口：表达、推演、数据。")

def slide3(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "DATA FIRST", "先把数据搞清楚，再谈系统", "24 块 DEM 瓦片 → 12,121 个 OSM 要素 → 三套情景帧", 3)
    pic_fit(s, FIG / "fig_pipeline.png", 0.65, 2.0, 12.0, 2.85, border=False)
    items = [("真实", "DEM / OSM / ERA5 / 官方阈值", CYAN), ("可复现", "7 个管线脚本，一键重跑", TEAL), ("有边界", "管网/实测缺失，明确说明", AMBER)]
    for i, (t, d, c) in enumerate(items):
        x = 0.65 + i * 4.18
        rect(s, x, 5.15, 3.92, 1.22, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
        text(s, x + 0.2, 5.28, 3.4, 0.35, t, size=14, color=c, bold=True)
        text(s, x + 0.2, 5.68, 3.45, 0.5, d, size=10, color=MUTED)
    text(s, 0.65, 6.65, 12, 0.35, "数据不是配角，而是整个系统的“地基”；地基不清，三维越漂亮越危险。", size=10.5, color=MUTED)
    notes(s, "这一页是方法论。我们先跑通数据管线：采集、清洗、融合、建模、校核、发布，七个脚本可复现。三类数据是真实的，管网和实测没有公开，我们明确用概化能力场和虚拟点位替代。")

def slide4(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "STUDY AREA", "26.7 km² 的福田数字底座", "莲花山—中心公园—福田 CBD—华强北—会展中心", 4)
    pic_fit(s, FIG / "fig_study_area.png", 0.6, 2.0, 7.9, 4.95)
    rows = [("研究范围", "6.18 × 4.32 km"), ("地形", "0.6—159.5 m"), ("建筑", "3,871 栋"), ("道路", "3,108 条"), ("监测点", "16 个"), ("人口", "约 78.9 万")]
    for i, (k, v) in enumerate(rows):
        y = 2.05 + i * 0.78
        text(s, 8.85, y, 1.6, 0.3, k, size=10, color=MUTED)
        text(s, 10.45, y - 0.02, 2.3, 0.35, v, size=15, color=TEXT, font=NUM, bold=True)
        ln = s.shapes.add_connector(1, Inches(8.85), Inches(y + 0.46), Inches(12.7), Inches(y + 0.46))
        ln.line.color.rgb = RGBColor(0x16, 0x30, 0x44); ln.line.width = Pt(0.5)
    text(s, 8.85, 6.55, 3.9, 0.45, "地形“北山南城、低洼沿河”，是内涝叙事的天然舞台。", size=9.5, color=TEAL)
    notes(s, "研究区26.7平方公里，北边莲花山、笔架山，南边CBD和深圳河。3,871栋建筑，最高平安金融中心599米。16个监测点不是随机撒的，是用50年一遇的积水包络做模型辅助选址。")

def slide5(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "DATA BOUNDARY", "真实与模拟的边界，必须说清楚", "课程设计最怕“伪精确”，我们选择主动标注", 5)
    rect(s, 0.65, 2.0, 5.9, 4.6, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
    text(s, 0.9, 2.18, 4.5, 0.3, "真实公开数据", size=13, color=TEAL, bold=True)
    multi(s, 0.9, 2.62, 5.4, 3.6, [
        "5 m DEM：Mapzen Terrarium / AWS Open Data",
        "建筑、道路、水系：OpenStreetMap（ODbL）",
        "历史降雨：Open-Meteo ERA5-Land（CC-BY）",
        "街道阈值：深圳 2025 年版官方指引",
        "设计暴雨：深圳 2024 版分流域公式",
    ], size=11, color=TEXT, bullet=True, space=7)
    rect(s, 6.85, 2.0, 5.9, 4.6, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
    text(s, 7.1, 2.18, 4.8, 0.3, "模拟 / 估算数据", size=13, color=AMBER, bold=True)
    multi(s, 7.1, 2.62, 5.35, 3.6, [
        "地下管网：未公开 → 概化排水能力场（12—60 mm/h）",
        "16 个监测点：模型辅助选址的虚拟点位",
        "建筑高度：38.1% 显式，61.9% 按类型/面积估算",
        "人口：按建筑体量估算，仅用于相对量级",
        "河道边界：未耦合潮位/顶托，是已知局限",
    ], size=11, color=TEXT, bullet=True, space=7)
    text(s, 0.65, 6.82, 12, 0.3, "原则：不伪造管网、不冒充实时监测、不隐瞒数据来源。", size=10.5, color=RED)
    notes(s, "这一页可能是答辩最容易被问的。真实数据是DEM、OSM、ERA5和官方阈值；管网、逐点易涝点、实测水位没有公开，我们用概化能力场和虚拟点位替代。建筑高度只有38%有显式值，其余估算。")

def slide6(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "MODEL", "从降雨到积水：四步耦合", "32 m 网格 · 6 s 步长 · 8 h 窗口 · 49 帧", 6)
    steps = [
        ("01", "产流", "SCS-CN", "Q =(P−0.2S)² /(P+0.8S)\n绿地 58 / 道路 96", CYAN),
        ("02", "汇流", "二维扩散波", "Manning 通量\n四邻域 · 建筑绕行", TEAL),
        ("03", "排水", "概化能力场", "12—60 mm/h\n超载后地面积水", AMBER),
        ("04", "输出", "10 min 帧", "水深 / 面积 / 人口\n16 点水位序列", PURPLE),
    ]
    for i, (n, t, sub, d, c) in enumerate(steps):
        x = 0.65 + i * 3.12
        rect(s, x, 2.05, 2.86, 3.2, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
        text(s, x + 0.18, 2.18, 0.6, 0.3, n, size=10, color=c, font=NUM, bold=True)
        text(s, x + 0.18, 2.5, 2.4, 0.4, t, size=17, color=TEXT, bold=True)
        text(s, x + 0.18, 2.95, 2.45, 0.3, sub, size=10, color=c)
        text(s, x + 0.18, 3.38, 2.45, 1.4, d, size=9.5, color=MUTED, line_spacing=1.5)
        if i < 3:
            text(s, x + 2.89, 3.35, 0.3, 0.3, "›", size=22, color=RGBColor(0x2C, 0x5A, 0x76))
    text(s, 0.65, 5.55, 12, 0.35, "为什么不用 SWMM/ICM？——管网数据不可得；课程场景要的是“可解释、可复现、分钟级”。", size=11, color=MUTED)
    text(s, 0.65, 6.08, 12, 0.8, "校验：三情景水量闭合率 0.875—0.895；峰值水深 0.42 / 1.55 / 2.33 m，量级合理；明确未做逐点实测率定。", size=11, color=TEAL)
    notes(s, "模型四步：SCS-CN产流、二维扩散波汇流、概化管网排水、输出10分钟帧。没有用SWMM，因为管网数据不可得；我们选可解释、可复现的简化模型，并如实说明未做实测率定。")

def slide7(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "SCENARIOS", "三类情景：标准内、标准外、历史极端", "9·7 复盘 / 50 年一遇 / 5 年一遇", 7)
    pic_fit(s, FIG / "fig_hyetograph.png", 0.65, 2.0, 7.7, 3.9)
    cards = [("9·7 复盘", "300 mm / 81 mm/h", "双峰，退水后再涨", RED),
             ("50 年一遇", "340 mm / 96 mm/h", "单峰偏后，最不利", AMBER),
             ("5 年一遇", "140 mm / 44.5 mm/h", "低洼点短时积水", CYAN)]
    for i, (t, d, s2, c) in enumerate(cards):
        y = 2.05 + i * 1.35
        rect(s, 8.65, y, 4.0, 1.15, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
        rect(s, 8.65, y, 0.05, 1.15, c)
        text(s, 8.84, y + 0.12, 3.6, 0.3, t, size=13, color=c, bold=True)
        text(s, 8.84, y + 0.47, 3.6, 0.3, d, size=11, color=TEXT, font=NUM)
        text(s, 8.84, y + 0.79, 3.6, 0.25, s2, size=9, color=MUTED)
    text(s, 0.65, 6.2, 12, 0.5, "设计暴雨采用深圳 2024 版中部流域公式，非经验假定；9·7 按官方实况总量校准。", size=10, color=MUTED)
    notes(s, "三套情景：9·7按官方实况校准，300毫米、峰值81；50年一遇340毫米、峰值96；5年一遇140毫米、峰值44.5。设计暴雨用深圳2024版中部流域公式，不是随手编的。")

def slide8(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "RESULT", "50 年一遇：水最深到哪里？", "8 h 预报窗口的最大积水深度包络面", 8)
    pic_fit(s, FIG / "fig_maxdepth.png", 0.55, 1.90, 7.5, 5.15)
    stats = [("2.33", "m", "全域最大水深", RED), ("299", "ha", "最大积水面积", AMBER), ("58,236", "人", "峰值受影响人口", CYAN)]
    for i, (v, u, lab, c) in enumerate(stats):
        y = 2.0 + i * 1.42
        text(s, 8.45, y, 3.8, 0.55, v, size=32, color=c, font=NUM, bold=True)
        text(s, 8.45 + (1.35 if len(v) < 5 else 2.0), y + 0.26, 0.8, 0.3, u, size=10, color=MUTED)
        text(s, 8.45, y + 0.70, 3.8, 0.3, lab, size=10, color=MUTED)
        ln = s.shapes.add_connector(1, Inches(8.45), Inches(y + 1.10), Inches(12.65), Inches(y + 1.10))
        ln.line.color.rgb = RGBColor(0x16, 0x30, 0x44); ln.line.width = Pt(0.5)
    text(s, 8.45, 6.35, 4.2, 0.6, "约 11.2% 的研究区出现 >15 cm 积水；16 个点位全部触发预警。", size=9.5, color=TEAL)
    notes(s, "50年一遇是最不利工况：最大2.33米，出现在会展中心周边低洼处；积水299公顷，约11%的研究区；峰值影响5.8万人。16个点位全部触发预警。")

def slide9(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "DIGITAL TWIN", "不是二维色块，是会起伏的三维水面", "Three.js / WebGL2 · 47k 地形顶点 · 3,871 栋建筑 · 7,000 条雨线", 9)
    pic_fit(s, FIG / "shot_50.png", 0.55, 1.95, 8.5, 4.78)
    feats = [("地形", "5 m DEM + 等高线", CYAN), ("建筑", "合并几何 + 窗光 Shader", TEAL), ("水面", "顶点随地形 + 深度着色", PURPLE), ("雨幕", "跟随相机 + 雨强联动", CYAN), ("监测", "光柱 + 脉冲 + 标签", AMBER), ("后处理", "Bloom + FXAA + ACES", TEAL)]
    for i, (t, d, c) in enumerate(feats):
        y = 2.0 + i * 0.76
        rect(s, 9.25, y, 3.45, 0.64, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
        text(s, 9.4, y + 0.08, 0.9, 0.25, t, size=9, color=c, bold=True)
        text(s, 10.2, y + 0.08, 2.3, 0.45, d, size=8.5, color=MUTED)
    notes(s, "三维不是贴图：地形有等高线，建筑是真实轮廓挤出，水面顶点跟着地形起伏，雨幕跟随相机。所有几何合并绘制，保证性能。")

def slide10(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "WARNING", "五级预警 + 一点一策", "水深判定、趋势判断、街道阈值、处置建议", 10)
    pic_fit(s, FIG / "shot_replay.png", 0.55, 1.95, 8.35, 4.7)
    levels = [("紫色", "≥100 cm", PURPLE), ("红色", "50—100", RED), ("橙色", "30—50", AMBER), ("黄色", "15—30", RGBColor(0xFF, 0xD1, 0x66)), ("蓝色", "5—15", RGBColor(0x4D, 0xA3, 0xFF))]
    for i, (n, d, c) in enumerate(levels):
        y = 1.98 + i * 0.58
        rect(s, 9.15, y, 3.55, 0.46, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
        text(s, 9.3, y + 0.08, 0.6, 0.25, n, size=9.5, color=c, bold=True)
        text(s, 10.0, y + 0.08, 2.5, 0.25, d + " cm", size=9, color=MUTED, font=NUM)
    text(s, 9.15, 5.05, 3.6, 1.2, "下穿隧道阈值 ×0.62，河道 ×1.6；\n趋势用 20 min 差值；点击点位看 49 帧过程线。", size=9.2, color=TEAL, line_spacing=1.45)
    text(s, 0.65, 6.85, 12, 0.3, "与深圳 2025 年版“街道阈值 + 五级色标”方法论一致，落到点位水深。", size=9.5, color=MUTED)
    notes(s, "预警分五级，和深圳2025版方法一致，但我们落到点位水深。下穿隧道阈值调低，因为风险更高。点击任何一个告警，可以看49帧过程线和处置建议。")

def slide11(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "DISPATCH", "从“看到”到“处置”：P0—P3 闭环", "按等级、点位类型、责任队伍、时限自动生成", 11)
    pic_fit(s, FIG / "shot_modal.png", 0.55, 1.95, 6.5, 4.8)
    rows = [("P0", "封闭 + 抽排 + 撤离", "紫/红，下穿 ≥30 cm", RED),
            ("P1", "预置泵车 + 交通管制", "橙，30—50 cm", AMBER),
            ("P2", "加密巡查 + 清理雨水口", "黄，15—30 cm", RGBColor(0xFF, 0xD1, 0x66)),
            ("P3", "常态监测 + 信息报送", "蓝/正常", TEAL)]
    for i, (p, a, cdt, c) in enumerate(rows):
        y = 2.0 + i * 1.12
        rect(s, 7.45, y, 5.25, 0.94, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
        rect(s, 7.45, y, 0.06, 0.94, c)
        text(s, 7.6, y + 0.1, 0.55, 0.3, p, size=12, color=c, font=NUM, bold=True)
        text(s, 8.2, y + 0.08, 4.3, 0.3, a, size=11.5, color=TEXT, bold=True)
        text(s, 8.2, y + 0.46, 4.3, 0.25, cdt, size=8.8, color=MUTED)
    text(s, 7.45, 6.55, 5.2, 0.4, "当前为规则生成；下一步接入“叫应”回执与工单闭环。", size=9, color=TEAL)
    notes(s, "处置不是一句“注意安全”，而是按等级给动作、责任队伍和时限。P0封闭抽排，P1预置，P2巡查，P3常态。下一步接叫应回执，形成真正的闭环。")

def slide12(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "ARCHITECTURE", "端—云—模型—应用，四层解耦", "静态 JSON + Node API，前端只负责“取数—渲染—交互”", 12)
    pic_fit(s, FIG / "fig_architecture.png", 0.55, 1.95, 7.6, 4.95, border=False)
    stack = [("渲染", "Three.js 0.180 / WebGL2", CYAN), ("前端", "原生 ESM + Canvas 2D", TEAL), ("服务", "Node 24 · 零依赖", AMBER), ("管线", "Python · NumPy · Pillow", PURPLE), ("数据", "JSON / 情景帧 / 静态资源", MUTED)]
    for i, (k, v, c) in enumerate(stack):
        y = 2.0 + i * 0.92
        text(s, 8.55, y, 0.8, 0.3, k, size=9, color=c, bold=True)
        text(s, 9.35, y - 0.02, 3.55, 0.4, v, size=11, color=TEXT)
        ln = s.shapes.add_connector(1, Inches(8.55), Inches(y + 0.48), Inches(12.8), Inches(y + 0.48))
        ln.line.color.rgb = RGBColor(0x16, 0x30, 0x44); ln.line.width = Pt(0.5)
    text(s, 8.55, 6.55, 4.2, 0.45, "换后端不改前端：JSON 契约稳定。", size=9, color=TEAL)
    notes(s, "架构四层解耦，前端Three.js，服务端Node零依赖，模型用Python离线跑。JSON契约稳定，未来换PostGIS/FastAPI，前端不用改。")

def slide13(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    header(s, "TEAM", "四个人，四条线，一个可运行的版本", "按模块边界分，不按“谁有空”分", 13)
    rows = [("A · 队长", "数据 / 模型", "DEM·OSM·降雨、SCS-CN、二维模型、报告统稿", "30%"),
            ("B", "三维 / 前端", "地形/建筑/水面 Shader、相机、交互、性能", "28%"),
            ("C", "平台 / 集成", "Node API、数据契约、部署、测试", "22%"),
            ("D", "产品 / 表达", "UI/UX、PPT、视频、答辩串讲", "20%")]
    for i, (who, role, task, pct) in enumerate(rows):
        y = 2.0 + i * 0.88
        rect(s, 0.65, y, 8.1, 0.74, PANEL, line=RGBColor(0x1B, 0x3A, 0x50))
        text(s, 0.82, y + 0.1, 1.05, 0.3, who, size=10.5, color=CYAN, bold=True)
        text(s, 1.9, y + 0.1, 1.7, 0.3, role, size=10, color=TEAL)
        text(s, 3.55, y + 0.1, 4.4, 0.3, task, size=9, color=MUTED)
        text(s, 7.95, y + 0.08, 0.6, 0.3, pct, size=12, color=AMBER, font=NUM, align=PP_ALIGN.RIGHT)
    # 六周里程碑时间线
    rect(s, 0.9, 5.98, 11.7, 0.02, RGBColor(0x1F, 0x4A, 0x66))
    ms = [("W1", "数据可用"), ("W2", "数字底座"), ("W3", "首情景"), ("W4", "系统 80%"), ("W5", "报告/PPT"), ("W6", "提交答辩")]
    for i, (w, lab) in enumerate(ms):
        x = 0.9 + i * 2.34
        dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x - 0.07), Inches(5.92), Inches(0.14), Inches(0.14))
        solid(dot, CYAN if i < 4 else AMBER); dot.line.fill.background()
        text(s, x - 0.35, 5.55, 0.8, 0.25, w, size=8.5, color=CYAN if i < 4 else AMBER, font=NUM, bold=True)
        text(s, x - 0.55, 6.18, 1.2, 0.25, lab, size=8.2, color=MUTED, align=PP_ALIGN.CENTER)
    text(s, 0.65, 7.02, 12, 0.25, "每周一计划、周四风险、周五联调；答辩前 48 h 冻结代码。", size=8.5, color=MUTED)
    notes(s, "四个人四条线：A数据模型，B三维前端，C平台集成，D产品表达。按模块边界分，接口先行，每周五联调。系统已经到80%，剩下的20%按这个表继续。")

def slide14(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s)
    rect(s, 0, 0, W, H, BG)
    pic_fit(s, FIG / "shot_50.png", 5.0, 0, 8.4, 7.5, border=False)
    rect(s, 0, 0, 7.6, H, BG, alpha=0.92)
    text(s, 0.8, 0.85, 4.8, 0.3, "SUMMARY", size=9.5, color=CYAN, font=NUM, bold=True)
    text(s, 0.8, 1.25, 5.8, 0.8, "三个关键词", size=30, color=TEXT, bold=True)
    items = [("数据先行", "真实 DEM/OSM/降雨 + 明确数据边界", CYAN),
             ("三维可感知", "地形起伏、建筑天际线、动态水面", TEAL),
             ("处置可闭环", "五级预警 → P0—P3 → 责任与时限", AMBER)]
    for i, (t, d, c) in enumerate(items):
        y = 2.35 + i * 1.05
        text(s, 0.8, y, 0.5, 0.3, f"0{i+1}", size=11, color=c, font=NUM, bold=True)
        text(s, 1.35, y - 0.03, 2.2, 0.35, t, size=15, color=TEXT, bold=True)
        text(s, 3.05, y, 4.1, 0.35, d, size=10, color=MUTED)
    text(s, 0.8, 5.65, 6.2, 0.9, "局限：管网未耦合、河道未动态边界、未做实测率定。\n下一步：接入真实站点与管网，延长退水窗口，做小区级试点。", size=9.5, color=MUTED, line_spacing=1.5)
    text(s, 0.8, 6.85, 5.2, 0.35, "谢谢，欢迎提问。", size=12, color=TEAL, bold=True)
    notes(s, "总结三个关键词：数据先行、三维可感知、处置可闭环。我们也清楚局限：管网、河道、实测率定都还没做。下一步接真实站点和管网，做小区级试点。谢谢大家。")

def main():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    for fn in [slide1, slide2, slide3, slide4, slide5, slide6, slide7, slide8, slide9, slide10, slide11, slide12, slide13, slide14]:
        fn(prs)
    prs.core_properties.title = "深澜 · 城市积水风险智慧预警平台"
    prs.core_properties.author = "第 4 小组"
    prs.save(OUT)
    print("保存", OUT, OUT.stat().st_size / 1e6, "MB", "slides", len(prs.slides))


if __name__ == "__main__":
    main()
