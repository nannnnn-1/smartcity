# -*- coding: utf-8 -*-
"""生成视频片头/片尾卡。"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import random, math

OUT = Path(__file__).resolve().parent.parent / "video"
W, H = 1280, 720
FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"
if not Path(FONT_B).exists():
    FONT_B = FONT


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def bg():
    im = Image.new("RGB", (W, H), (4, 9, 17))
    d = ImageDraw.Draw(im)
    # 渐变
    for y in range(H):
        t = y / H
        c = (int(4 + 6 * (1 - t)), int(10 + 18 * (1 - t)), int(20 + 28 * (1 - t)))
        d.line([(0, y), (W, y)], fill=c)
    # 细网格
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=(12, 30, 44), width=1)
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=(10, 26, 39), width=1)
    # 雨丝
    random.seed(7)
    for _ in range(240):
        x = random.randint(-100, W); y = random.randint(-50, H)
        ln = random.randint(18, 60)
        d.line([(x, y), (x + 8, y + ln)], fill=(38, 92, 120), width=1)
    # 光晕
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-200, 260, 700, 900], fill=(20, 100, 130, 40))
    gd.ellipse([700, -200, 1300, 500], fill=(20, 70, 120, 30))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    im = Image.alpha_composite(im.convert("RGBA"), glow).convert("RGB")
    return im


def accent(d, x, y, w=150):
    d.rectangle([x, y, x + w, y + 3], fill=(53, 208, 165))
    d.rectangle([x + w + 8, y, x + w + 26, y + 3], fill=(95, 215, 255))


def title():
    im = bg(); d = ImageDraw.Draw(im)
    # logo 六边形
    cx, cy, r = 118, 112, 30
    pts = [(cx + r * math.cos(math.radians(60 * i - 30)), cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
    d.line(pts + [pts[0]], fill=(95, 215, 255), width=2)
    d.line([(cx - 16, cy + 6), (cx - 4, cy - 10), (cx + 6, cy + 2), (cx + 18, cy - 12)], fill=(95, 215, 255), width=3, joint="curve")
    d.text((162, 80), "《智慧城市》课程结课设计", font=font(22), fill=(53, 208, 165))
    d.text((160, 120), "SHENLAN · URBAN FLOOD DIGITAL TWIN", font=font(12), fill=(94, 130, 155))
    d.text((84, 210), "深澜", font=font(92, True), fill=(238, 249, 255))
    d.text((88, 330), "城市积水风险智慧预警平台", font=font(40, True), fill=(238, 249, 255))
    d.text((90, 392), "深圳福田数字孪生 · 数据驱动的三维推演", font=font(22), fill=(140, 170, 195))
    accent(d, 90, 448, 140)
    d.text((90, 478), "2023·9·7 复盘   /   50 年一遇   /   5 年一遇", font=font(19), fill=(95, 215, 255))
    d.text((90, 560), "第 4 小组   ·   2026 年 11 月", font=font(18), fill=(120, 150, 175))
    d.text((90, 660), "数据先行  ·  三维可感知  ·  处置可闭环", font=font(13), fill=(70, 110, 138))
    im.save(OUT / "title.png")


def outro():
    im = bg(); d = ImageDraw.Draw(im)
    d.text((84, 120), "SUMMARY", font=font(14), fill=(95, 215, 255))
    d.text((82, 158), "三个关键词", font=font(54, True), fill=(238, 249, 255))
    rows = [("01", "数据先行", "真实 DEM / OSM / 降雨 + 明确数据边界", (95, 215, 255)),
            ("02", "三维可感知", "地形起伏、建筑天际线、动态水面", (53, 208, 165)),
            ("03", "处置可闭环", "五级预警 → P0—P3 → 责任与时限", (255, 193, 94))]
    for i, (n, t, s, c) in enumerate(rows):
        y = 290 + i * 92
        d.text((86, y), n, font=font(18, True), fill=c)
        d.text((146, y - 6), t, font=font(30, True), fill=(238, 249, 255))
        d.text((340, y), s, font=font(17), fill=(140, 170, 195))
    d.text((86, 610), "谢谢观看  ·  欢迎提问", font=font(24, True), fill=(53, 208, 165))
    d.text((86, 660), "第 4 小组  ·  数据 / 模型  ·  三维 / 前端  ·  平台 / 集成  ·  产品 / 表达", font=font(12), fill=(90, 125, 150))
    im.save(OUT / "outro.png")


if __name__ == "__main__":
    title(); outro()
    print("cards done")
