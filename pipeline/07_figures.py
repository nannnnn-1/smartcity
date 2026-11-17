# -*- coding: utf-8 -*-
"""生成设计报告与 PPT 所需的图表（高分辨率 PNG）。"""
import json, base64, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, LightSource
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import matplotlib.patheffects as pe
from config import ROOT, PROCESSED, WEB_DATA

FIG = ROOT / "docs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
FONT = r"C:\Windows\Fonts\msyh.ttc"
if not Path(FONT).exists():
    FONT = r"C:\Windows\Fonts\simhei.ttf"
fp = font_manager.FontProperties(fname=FONT)
plt.rcParams["font.family"] = fp.get_name()
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "#07111f"
plt.rcParams["axes.facecolor"] = "#07111f"
plt.rcParams["savefig.facecolor"] = "#07111f"
TXT = "#dcecf9"
MUTED = "#7f9bb5"
CYAN = "#5fd7ff"
TEAL = "#35d0a5"
AMBER = "#ffc15e"
RED = "#ff4d5e"
PURPLE = "#c77dff"


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


meta = load_json(WEB_DATA / "meta.json")
sensors = load_json(WEB_DATA / "sensors.json")
vectors = load_json(WEB_DATA / "vectors.json")
scen_index = load_json(WEB_DATA / "scenarios" / "index.json")
scen = {s["id"]: load_json(WEB_DATA / "scenarios" / f"{s['id']}.json") for s in scen_index}
g = np.load(PROCESSED / "grid.npz")
z = g["z"]
W, H = float(g["W"]), float(g["H"])
NX, NY = g["z"].shape[1], g["z"].shape[0]
KM = 1000.0


def blur(a, passes=3):
    for _ in range(passes):
        a = (4*a + 2*(np.roll(a,1,0)+np.roll(a,-1,0)+np.roll(a,1,1)+np.roll(a,-1,1))
             + np.roll(np.roll(a,1,0),1,1)+np.roll(np.roll(a,1,0),-1,1)
             + np.roll(np.roll(a,-1,0),1,1)+np.roll(np.roll(a,-1,0),-1,1)) / 16.0
    return a


def style_ax(ax):
    for s in ax.spines.values():
        s.set_color("#1b3450")
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.xaxis.label.set_color(MUTED); ax.yaxis.label.set_color(MUTED)
    ax.title.set_color(TXT)


def envelope(sid):
    arr = np.zeros((NY, NX), np.float32)
    for f in scen[sid]["frames"]:
        a = np.frombuffer(base64.b64decode(f["depth"]), np.uint8).reshape(NY, NX)
        arr = np.maximum(arr, a)
    return arr


# ------------------------------------------------------------------ 1 研究区
def fig_study_area():
    fig, ax = plt.subplots(figsize=(11, 7.6), dpi=200)
    ls = LightSource(azdeg=315, altdeg=45)
    hs = ls.hillshade(np.clip(z, 0, None), vert_exag=1.5, dx=W / NX, dy=H / NY)
    ax.imshow(hs, cmap="gray", extent=(0, W / KM, H / KM, 0), alpha=0.55, vmin=0, vmax=1)
    ax.imshow(z, cmap="terrain", extent=(0, W / KM, H / KM, 0), alpha=0.28)
    for r in vectors["roads"]:
        p = np.array(r["p"]).reshape(-1, 2) / KM
        if r["c"] in ("motorway", "trunk", "primary"):
            ax.plot(p[:, 0], p[:, 1], color="#7ec8e8", lw=1.2, alpha=0.55)
        elif r["c"] in ("secondary", "tertiary"):
            ax.plot(p[:, 0], p[:, 1], color="#4c7f9e", lw=0.55, alpha=0.42)
    for w in vectors["water"]:
        p = np.array(w["p"]).reshape(-1, 2) / KM
        ax.fill(p[:, 0], p[:, 1], color="#1d6f9e", alpha=0.85, lw=0)
    for r in vectors["rivers"]:
        p = np.array(r["p"]).reshape(-1, 2) / KM
        ax.plot(p[:, 0], p[:, 1], color="#38b6e8", lw=max(1.2, r["w"] / 18), alpha=0.85)
    for s in sensors:
        ax.plot(s["x"] / KM, s["z"] / KM, "o", ms=5.5, mfc="#ffcf5e", mec="#07111f", mew=0.8, zorder=8)
        ax.annotate(s["id"], (s["x"] / KM, s["z"] / KM), xytext=(4, 4), textcoords="offset points",
                    color="#ffe9b0", fontsize=6.4, zorder=9)
    for name, lon, lat in [("莲花山", 114.055, 22.557), ("中心公园", 114.065, 22.547),
                           ("福田CBD", 114.060, 22.538), ("华强北", 114.082, 22.545),
                           ("市民中心", 114.058, 22.543), ("深圳会展中心", 114.055, 22.534)]:
        x = (lon - 114.040) * 102924.0 / KM
        y = (22.572 - lat) * 110852.0 / KM
        ax.text(x, y, name, color="#eaf8ff", fontsize=8.5, ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=2.5, foreground="#04101c")], zorder=10)
    # 比例尺、指北针
    ax.plot([0.25, 1.25], [4.28, 4.28], color="#eaf8ff", lw=2)
    ax.text(0.75, 4.18, "1 km", color="#eaf8ff", fontsize=8, ha="center")
    ax.annotate("N", xy=(5.45, 0.25), xytext=(5.45, 0.65), color="#eaf8ff", fontsize=11,
                ha="center", arrowprops=dict(arrowstyle="-|>", color="#eaf8ff", lw=1.4))
    ax.set_xlim(0, W / KM); ax.set_ylim(H / KM, 0)
    ax.set_xlabel("东向距离 / km"); ax.set_ylabel("南向距离 / km")
    ax.set_title("研究区：深圳福田 26.7 km² 数字孪生范围（DEM + OSM + 16 个监测点）", fontsize=12, pad=12)
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(FIG / "fig_study_area.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 2 降雨
def fig_hyetograph():
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=200)
    colors = {"replay-2309": RED, "design-50": AMBER, "design-5": CYAN}
    labels = {"replay-2309": "2023·9·7 复盘（300 mm）", "design-50": "50 年一遇（340 mm）", "design-5": "5 年一遇（140 mm）"}
    for sid in ["replay-2309", "design-50", "design-5"]:
        rain = np.array(scen[sid]["rain"])
        ax.plot(np.arange(len(rain)) / 60, rain, color=colors[sid], lw=1.8, label=labels[sid])
        ax.fill_between(np.arange(len(rain)) / 60, rain, color=colors[sid], alpha=0.10)
    ax.axhline(30, color="#8fa9bf", ls="--", lw=0.8)
    ax.text(0.05, 31.5, "概化管网排水能力 30 mm/h（基准）", color="#8fa9bf", fontsize=7.5)
    ax.set_xlim(0, 8); ax.set_xlabel("历时 / h"); ax.set_ylabel("雨强 / (mm/h)")
    ax.set_title("三类情景设计暴雨过程线", fontsize=12)
    ax.grid(alpha=0.12, color="#7f9bb5")
    leg = ax.legend(facecolor="#0a1a2b", edgecolor="#1b3450", labelcolor=TXT, fontsize=8)
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(FIG / "fig_hyetograph.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 3 最大水深
def fig_maxdepth():
    cmap = LinearSegmentedColormap.from_list("flood", ["#1b4f72", "#2e86c1", "#5dade2", "#a569bd", "#e74c3c"])
    sid = "design-50"
    raw_env = envelope(sid)
    env = blur(raw_env, 5)
    fig, ax = plt.subplots(figsize=(10, 7.2), dpi=200)
    ax.imshow(np.clip(z, 0, None), cmap="gray", extent=(0, W / KM, H / KM, 0), alpha=0.72)
    for r in vectors["roads"]:
        p = np.array(r["p"]).reshape(-1, 2) / KM
        if r["c"] in ("primary", "secondary", "trunk"):
            ax.plot(p[:, 0], p[:, 1], color="#93b7cc", lw=0.45, alpha=0.28)
    m = np.ma.masked_less(env, 8)
    im = ax.imshow(m, cmap=cmap, extent=(0, W / KM, H / KM, 0), alpha=0.94, vmin=0, vmax=150)
    for s in sensors:
        ax.plot(s["x"] / KM, s["z"] / KM, "o", ms=3.2, mfc="#fff", mec="#07111f", mew=0.4, zorder=5)
    for name, lon, lat in [("莲花山", 114.055, 22.557), ("中心公园", 114.065, 22.547),
                           ("福田CBD", 114.060, 22.538), ("华强北", 114.082, 22.545),
                           ("会展中心", 114.055, 22.534)]:
        x = (lon - 114.040) * 102924.0 / KM
        y = (22.572 - lat) * 110852.0 / KM
        ax.text(x, y, name, color="#eaf8ff", fontsize=9, ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=2.4, foreground="#04101c")], zorder=6)
    st = scen[sid]["stats"]
    ax.set_title(f"50 年一遇最大积水深度包络面", fontsize=15, pad=10)
    ax.text(0.015, 0.985, f"最大水深 {st['maxDepth']:.2f} m ｜ 积水面积 {st['maxAreaHa']:.0f} ha ｜ 峰值人口 {st['maxPop']:,} 人",
            transform=ax.transAxes, color="#eaf8ff", fontsize=9.5, va="top",
            bbox=dict(fc="#07111f", ec="#2a5a78", alpha=0.88, pad=6))
    my, mx = np.unravel_index(np.argmax(raw_env), raw_env.shape)
    ax.plot(mx / NX * W / KM, my / NY * H / KM, "x", color="#ff4d5e", ms=11, mew=2.4, zorder=7)
    ax.annotate(f"{raw_env[my, mx]/100:.2f} m", (mx / NX * W / KM, my / NY * H / KM),
                xytext=(8, -14), textcoords="offset points", color="#ffb3bb", fontsize=9,
                path_effects=[pe.withStroke(linewidth=2, foreground="#04101c")], zorder=8)
    ax.set_xlim(0, W / KM); ax.set_ylim(H / KM, 0)
    ax.set_xlabel("东向距离 / km"); ax.set_ylabel("南向距离 / km")
    style_ax(ax)
    cax = fig.add_axes([0.90, 0.16, 0.018, 0.64])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("最大水深 / cm", color=TXT, fontsize=9)
    cb.ax.tick_params(colors=MUTED, labelsize=8)
    cb.outline.set_edgecolor("#1b3450")
    fig.subplots_adjust(left=0.07, right=0.88, top=0.92, bottom=0.10)
    fig.savefig(FIG / "fig_maxdepth.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 4 监测点峰值
def fig_sensor_peaks():
    order = sorted(sensors, key=lambda s: max(scen["design-50"]["sensors"][i]["peak"] for i in range(len(sensors))
                                             if scen["design-50"]["sensors"][i]["id"] == s["id"]), reverse=True)[:12]
    fig, ax = plt.subplots(figsize=(10, 5.4), dpi=200)
    yy = np.arange(len(order))[::-1]
    h = 0.26
    for k, (sid, c, lab) in enumerate([("replay-2309", RED, "9·7 复盘"), ("design-50", AMBER, "50 年一遇"), ("design-5", CYAN, "5 年一遇")]):
        vals = []
        for s in order:
            v = next(x["peak"] for x in scen[sid]["sensors"] if x["id"] == s["id"])
            vals.append(v * 100)
        ax.barh(yy + (1 - k) * h, vals, height=h, color=c, alpha=0.88, label=lab)
    ax.set_yticks(yy)
    ax.set_yticklabels([f"{s['id']}  {s['name']}" for s in order], fontsize=8)
    ax.axvline(15, color="#ffd166", ls="--", lw=0.9)
    ax.axvline(30, color="#ff9f43", ls="--", lw=0.9)
    ax.axvline(50, color="#ff4d5e", ls="--", lw=0.9)
    ax.set_xlabel("监测点峰值水深 / cm")
    ax.set_title("16 个监测点在三种情景下的峰值水深（取前 12 位）", fontsize=12)
    ax.grid(axis="x", alpha=0.12, color="#7f9bb5")
    ax.legend(facecolor="#0a1a2b", edgecolor="#1b3450", labelcolor=TXT, fontsize=8, loc="lower right")
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(FIG / "fig_sensor_peaks.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 5 过程曲线
def fig_process():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), dpi=200)
    for sid, c, lab in [("replay-2309", RED, "9·7 复盘"), ("design-50", AMBER, "50 年一遇"), ("design-5", CYAN, "5 年一遇")]:
        t = [f["t"] / 60 for f in scen[sid]["frames"]]
        axes[0].plot(t, [f["maxDepth"] for f in scen[sid]["frames"]], color=c, lw=1.8, label=lab)
        axes[1].plot(t, [f["areaHa"] for f in scen[sid]["frames"]], color=c, lw=1.8, label=lab)
    axes[0].set_ylabel("全域最大水深 / m"); axes[1].set_ylabel("积水面积（>15 cm）/ ha")
    for ax in axes:
        ax.set_xlabel("历时 / h"); ax.grid(alpha=0.12, color="#7f9bb5")
        ax.legend(facecolor="#0a1a2b", edgecolor="#1b3450", labelcolor=TXT, fontsize=8)
        style_ax(ax)
    axes[0].set_title("最大水深过程", fontsize=11); axes[1].set_title("积水面积过程", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "fig_process.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 6 架构
def box(ax, x, y, w, h, title, sub, color, fs=8.5):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
                       fc=color + "18", ec=color, lw=1.1)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h - 0.018, title, ha="center", va="top", color=color, fontsize=fs + 0.8, weight="bold")
    ax.text(x + w / 2, y + h - 0.068, sub, ha="center", va="top", color="#a9c2d6", fontsize=fs - 1.1, linespacing=1.5)


def arrow(ax, x1, y1, x2, y2, color="#5fd7ff"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10,
                                 color=color, lw=1.0, alpha=0.8))


def fig_architecture():
    fig, ax = plt.subplots(figsize=(10.5, 7.0), dpi=200)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.5, 0.97, "系统总体架构", ha="center", color=TXT, fontsize=16)
    ax.text(0.5, 0.925, "感知 → 数据 → 模型/预警 → 应用 → 用户", ha="center", color=MUTED, fontsize=10)
    box(ax, 0.05, 0.79, 0.90, 0.10, "感知层 ｜ 城市内涝立体监测网",
        "积水水位 · 雨量 · 视频 · 管网液位 · 河道水位 · MQTT/HTTP 接入", CYAN, fs=10)
    box(ax, 0.05, 0.62, 0.90, 0.12, "数据层 ｜ 多源数据治理与数字底座",
        "DEM · OSM · ERA5 · 官方阈值 · 情景帧 · 参数/规则库 · PostGIS（规划）", TEAL, fs=10)
    box(ax, 0.05, 0.40, 0.43, 0.15, "模型层 ｜ 水文—水动力耦合",
        "SCS-CN 产流\n二维扩散波汇流\n概化排水能力场", AMBER, fs=10)
    box(ax, 0.52, 0.40, 0.43, 0.15, "预警层 ｜ 规则引擎",
        "五级色标 · 趋势判定\n热点排序 · P0—P3 处置", RED, fs=10)
    box(ax, 0.05, 0.20, 0.90, 0.14, "应用层 ｜ 三维数字孪生指挥舱",
        "三维态势 · 情景推演 · 时间轴回放 · 监测点详情 · 智能处置 · 大屏适配", CYAN, fs=10)
    box(ax, 0.05, 0.04, 0.90, 0.10, "用户层",
        "区三防指挥部 · 排水抢险队 · 街道网格员 · 公众（预留）", "#8fa9bf", fs=10)
    for y1, y2 in [(0.79, 0.74), (0.62, 0.55)]:
        arrow(ax, 0.5, y1, 0.5, y2)
    arrow(ax, 0.5, 0.40, 0.5, 0.34)
    arrow(ax, 0.5, 0.20, 0.5, 0.14)
    fig.tight_layout()
    fig.savefig(FIG / "fig_architecture.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 7 数据管线
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(13, 3.2), dpi=200)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    steps = [
        ("01 采集", "DEM 瓦片\nOSM 要素\nERA5 降雨", CYAN),
        ("02 清洗", "空洞填充\n噪声滤波\n坐标统一", TEAL),
        ("03 融合", "建筑高度推算\nCN/不透水面\n排水能力场", AMBER),
        ("04 建模", "SCS-CN\n二维扩散波\n情景降雨", "#ff9f43"),
        ("05 校核", "水量平衡\n峰值合理性\n情景对比", RED),
        ("06 发布", "10 min 帧\n传感器序列\n三维 JSON", PURPLE),
    ]
    w, gap = 0.135, 0.032
    for i, (t, s, c) in enumerate(steps):
        x = 0.02 + i * (w + gap)
        p = FancyBboxPatch((x, 0.22), w, 0.58, boxstyle="round,pad=0.008,rounding_size=0.02",
                           fc=c + "16", ec=c, lw=1.2)
        ax.add_patch(p)
        ax.text(x + w / 2, 0.70, t, ha="center", color=c, fontsize=9.5, weight="bold")
        ax.text(x + w / 2, 0.50, s, ha="center", va="center", color="#b9d3e6", fontsize=7.6, linespacing=1.7)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + w + gap - 0.004, 0.51), xytext=(x + w + 0.004, 0.51),
                        arrowprops=dict(arrowstyle="-|>", color="#4b7d9e", lw=1.3))
    ax.text(0.5, 0.92, "数据先行：从原始开放数据到可推演的三维数字底座", ha="center", color=TXT, fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG / "fig_pipeline.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 8 甘特图
def fig_gantt():
    tasks = [
        ("需求分析与数据源核验", 0, 1, "A"),
        ("DEM/OSM/降雨采集与清洗", 0.5, 2, "A"),
        ("水文模型与情景率定", 1.5, 3.2, "A"),
        ("三维场景与着色器", 1.5, 3.6, "B"),
        ("交互与可视化面板", 2.2, 4.2, "B/D"),
        ("API 与系统集成", 2.5, 4.2, "C"),
        ("测试、性能与部署", 3.8, 5.2, "C"),
        ("报告撰写与图表", 3.2, 5.4, "A/D"),
        ("PPT 与 3 分钟视频", 4.2, 5.8, "D"),
        ("答辩演练与终验", 5.4, 6.0, "全员"),
    ]
    colors = {"A": CYAN, "B": TEAL, "C": AMBER, "D": PURPLE, "全员": RED, "B/D": "#7ec8e8", "A/D": "#8ee6ff"}
    fig, ax = plt.subplots(figsize=(10.5, 5.0), dpi=200)
    for i, (name, s, e, who) in enumerate(tasks):
        y = len(tasks) - i - 1
        ax.barh(y, e - s, left=s, height=0.5, color=colors.get(who, CYAN), alpha=0.82,
                edgecolor="#07111f", linewidth=1)
        ax.text(s + 0.04, y, f"{who}", va="center", color="#04121d", fontsize=7, weight="bold")
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels([t[0] for t in tasks][::-1], fontsize=8)
    ax.set_xlim(0, 6.2); ax.set_xticks(range(7))
    ax.set_xticklabels([f"第{i}周" for i in range(7)], fontsize=8)
    ax.grid(axis="x", alpha=0.15, color="#7f9bb5")
    ax.set_title("六周实施计划与四人并行分工（A 数据/模型，B 三维/前端，C 平台/集成，D 产品/表达）", fontsize=10.5)
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(FIG / "fig_gantt.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_study_area()
    fig_hyetograph()
    fig_maxdepth()
    fig_sensor_peaks()
    fig_process()
    fig_architecture()
    fig_pipeline()
    fig_gantt()
    print("figures done ->", FIG)
