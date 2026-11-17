# -*- coding: utf-8 -*-
"""构建城市数字底座：地形、建筑、道路、水系、绿地、人口与监测点。

输入：data/raw/dem_crop.npy, data/raw/osm_raw.json
输出：
  data/processed/grid.npz              —— 水文模型网格（高程/CN/不透水率/建筑/水系/人口/排水能力）
  system/public/data/terrain.json      —— 三维地形（高程 + 地表类型）
  system/public/data/buildings.json    —— 建筑体块（底面 + 高度 + 名称）
  system/public/data/vectors.json      —— 道路/水系/绿地矢量
  system/public/data/sensors.json      —— 监测点
  system/public/data/meta.json         —— 场景元信息
"""
import json, math, hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from config import (ROOT, RAW, PROCESSED, WEB_DATA, LON_MIN, LON_MAX, LAT_MIN, LAT_MAX,
                    M_PER_DEG_LAT, M_PER_DEG_LON, GRID_NX, GRID_NY, RENDER_NX, RENDER_NY)

W = (LON_MAX - LON_MIN) * M_PER_DEG_LON
H = (LAT_MAX - LAT_MIN) * M_PER_DEG_LAT


# ---------------------------------------------------------------- 基础工具
def lonlat_to_xy(lon, lat):
    return (lon - LON_MIN) * M_PER_DEG_LON, (LAT_MAX - lat) * M_PER_DEG_LAT


def poly_area(pts):
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def gaussian_blur(a, sigma):
    if sigma <= 0:
        return a
    r = max(1, int(round(sigma * 2.5)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-(x ** 2) / (2 * sigma ** 2))
    k /= k.sum()
    pad = np.pad(a, r, mode="edge")
    tmp = np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 1, pad)
    out = np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 0, np.pad(tmp, ((r, r), (0, 0)), mode="edge"))
    # apply_along_axis 在 0 轴上卷积后尺寸会变化，做一次显式处理更稳妥
    return out[:a.shape[0], :a.shape[1]]


def box_blur(a, k=3):
    pad = k // 2
    p = np.pad(a, pad, mode="edge")
    c = np.cumsum(np.cumsum(p, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    out = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
    return out[:a.shape[0], :a.shape[1]]


def resample(a, nx, ny, mode="bilinear"):
    im = Image.fromarray(a.astype(np.float32), mode="F")
    im = im.resize((nx, ny), Image.BILINEAR if mode == "bilinear" else Image.NEAREST)
    return np.asarray(im, dtype=np.float64)


def resample_u8(a, nx, ny):
    im = Image.fromarray(a.astype(np.uint8), mode="L").resize((nx, ny), Image.BILINEAR)
    return np.asarray(im, dtype=np.uint8)


# ---------------------------------------------------------------- DEM
def load_dem():
    dem = np.load(RAW / "dem_crop.npy").astype(np.float64)
    dem[dem < -3] = np.nan
    # 南侧数据空洞：按列用最近有效值向下填充
    for j in range(dem.shape[1]):
        col = dem[:, j]
        idx = np.where(~np.isnan(col))[0]
        if len(idx) == 0:
            col[:] = 2.0
        else:
            # 先向下填充
            last = col[idx[0]]
            for i in range(dem.shape[0]):
                if np.isnan(col[i]):
                    col[i] = last
                else:
                    last = col[i]
    # 去建筑/树冠噪声：3x3 中值 + 高斯
    stack = np.stack([np.roll(np.roll(dem, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
    dem = np.median(stack, axis=0)
    dem = gaussian_blur(dem, 3.0)
    dem = np.clip(dem, 0.6, None)
    return dem


# ---------------------------------------------------------------- OSM 解析
def load_osm():
    d = json.load(open(RAW / "osm_raw.json", encoding="utf-8"))
    ways = [e for e in d["elements"] if e["type"] == "way" and "geometry" in e]
    buildings, roads, water_poly, river_lines, green_poly, pois = [], [], [], [], [], []
    for e in ways:
        t = e.get("tags", {})
        pts = [(g["lon"], g["lat"]) for g in e["geometry"]]
        if len(pts) < 2:
            continue
        xy = [lonlat_to_xy(lon, lat) for lon, lat in pts]
        if "building" in t:
            if len(xy) >= 3 and poly_area(xy) > 25:
                buildings.append((e, xy))
        if "highway" in t and t["highway"] not in ("footway", "steps", "path", "cycleway", "pedestrian", "corridor", "elevator", "platform"):
            roads.append((e, xy))
        if t.get("natural") == "water" or t.get("landuse") == "reservoir" or t.get("water"):
            if len(xy) >= 3 and poly_area(xy) > 80:
                water_poly.append((e, xy))
        if t.get("waterway") in ("river", "canal", "stream", "ditch"):
            river_lines.append((e, xy))
        if (t.get("landuse") in ("grass", "forest", "meadow", "flowerbed", "village_green")
                or t.get("leisure") in ("park", "garden", "pitch", "playground", "track", "fitness_station")
                or t.get("natural") in ("wood", "scrub", "grassland")):
            if len(xy) >= 3 and poly_area(xy) > 100:
                green_poly.append((e, xy))
    print(f"OSM: buildings={len(buildings)} roads={len(roads)} water_poly={len(water_poly)} "
          f"rivers={len(river_lines)} green={len(green_poly)}")
    return buildings, roads, water_poly, river_lines, green_poly


def estimate_height(t, area, eid):
    h = t.get("height")
    if h:
        try:
            v = float(str(h).lower().replace("m", "").strip())
            if 2 < v < 700:
                return v
        except Exception:
            pass
    lv = t.get("building:levels")
    if lv:
        try:
            v = float(str(lv).replace("层", "").strip())
            if 0 < v < 200:
                return max(3.2, v * 3.3 + 1.0)
        except Exception:
            pass
    kind = t.get("building", "yes")
    base = {"apartments": 8, "residential": 6, "commercial": 5, "office": 8, "retail": 3,
            "school": 4, "hospital": 7, "hotel": 10, "industrial": 4, "train_station": 12,
            "public": 5, "yes": 4}.get(kind, 4)
    rnd = int(hashlib.md5(str(eid).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    floors = base + rnd * 4
    if area > 1200:
        floors += 2
    return max(3.0, floors * 3.2 + 1.0)


# ---------------------------------------------------------------- 栅格化
def rasterize(dem_shape, buildings, roads, water_poly, river_lines, green_poly):
    hgt, wid = dem_shape
    sx = wid / W
    sy = hgt / H
    def to_px(pts):
        return [(x * sx, y * sy) for x, y in pts]

    m_build = Image.new("1", (wid, hgt), 0)
    db = ImageDraw.Draw(m_build)
    for e, xy in buildings:
        db.polygon(to_px(xy), fill=1)

    m_water = Image.new("1", (wid, hgt), 0)
    dw = ImageDraw.Draw(m_water)
    for e, xy in water_poly:
        dw.polygon(to_px(xy), fill=1)
    for e, xy in river_lines:
        wdt = max(3, int({"river": 22, "canal": 14, "stream": 7, "ditch": 5}.get(e["tags"].get("waterway"), 7) * sx))
        dw.line(to_px(xy), fill=1, width=wdt, joint="curve")

    m_green = Image.new("1", (wid, hgt), 0)
    dg = ImageDraw.Draw(m_green)
    for e, xy in green_poly:
        dg.polygon(to_px(xy), fill=1)

    m_road = Image.new("1", (wid, hgt), 0)
    dr = ImageDraw.Draw(m_road)
    widths = {"motorway": 45, "trunk": 40, "primary": 34, "secondary": 26, "tertiary": 18,
              "residential": 10, "service": 6, "unclassified": 10, "motorway_link": 12,
              "trunk_link": 12, "primary_link": 12, "secondary_link": 10, "tertiary_link": 8,
              "living_street": 8, "road": 8, "track": 4}
    for e, xy in roads:
        wdt = max(2, int(widths.get(e["tags"].get("highway"), 8) * sx))
        dr.line(to_px(xy), fill=1, width=wdt, joint="curve")

    b = np.asarray(m_build, dtype=np.uint8)
    w = np.asarray(m_water, dtype=np.uint8)
    g = np.asarray(m_green, dtype=np.uint8)
    r = np.asarray(m_road, dtype=np.uint8)
    return b, w, g, r


# ---------------------------------------------------------------- 监测点
SENSOR_ANCHORS = [
    ("SN-01", "深南大道·香蜜湖立交", "underpass", 114.0435, 22.5412, "车公庙片区"),
    ("SN-02", "滨河大道·益田路下穿", "underpass", 114.0562, 22.5336, "福田口岸片区"),
    ("SN-03", "福华三路·会展中心", "road", 114.0565, 22.5352, "会展中心片区"),
    ("SN-04", "金田路·皇岗村", "community", 114.0618, 22.5342, "皇岗片区"),
    ("SN-05", "彩田路·中心公园", "road", 114.0648, 22.5442, "中心公园片区"),
    ("SN-06", "华强北路·女人世界", "underpass", 114.0812, 22.5452, "华强北商圈"),
    ("SN-07", "上步路·荔枝公园", "road", 114.0752, 22.5472, "园岭片区"),
    ("SN-08", "红荔路·莲花山南门", "road", 114.0582, 22.5552, "莲花山片区"),
    ("SN-09", "新洲路·景田", "community", 114.0490, 22.5500, "景田片区"),
    ("SN-10", "香蜜湖路·车公庙", "road", 114.0418, 22.5382, "车公庙片区"),
    ("SN-11", "益田路·福民", "community", 114.0558, 22.5332, "福民片区"),
    ("SN-12", "北环大道·彩田", "road", 114.0652, 22.5688, "梅林片区"),
    ("SN-13", "中心公园排洪渠", "river", 114.0662, 22.5470, "中心公园片区"),
    ("SN-14", "市民中心广场", "community", 114.0588, 22.5422, "市民中心片区"),
    ("SN-15", "华强南·地下通道", "underpass", 114.0822, 22.5402, "华强南片区"),
    ("SN-16", "福中路·莲花村", "community", 114.0615, 22.5505, "莲花村片区"),
]


def build_sensors(dem, bmask, wmask):
    hgt, wid = dem.shape
    sx = wid / W
    sy = hgt / H
    sensors = []
    for sid, name, typ, lon, lat, comm in SENSOR_ANCHORS:
        x, z = lonlat_to_xy(lon, lat)
        cx, cy = int(x * sx), int(z * sy)
        r = 90  # 90 px ≈ 400 m
        x0, x1 = max(0, cx - r), min(wid, cx + r)
        y0, y1 = max(0, cy - r), min(hgt, cy + r)
        sub = dem[y0:y1, x0:x1].copy()
        sub[(bmask[y0:y1, x0:x1] == 1) | (wmask[y0:y1, x0:x1] == 1)] = 999
        iy, ix = np.unravel_index(np.argmin(sub), sub.shape)
        px, py = x0 + ix, y0 + iy
        sensors.append({
            "id": sid, "name": name, "type": typ, "community": comm,
            "lon": round(LON_MIN + (px + 0.5) / wid * (LON_MAX - LON_MIN), 6),
            "lat": round(LAT_MAX - (py + 0.5) / hgt * (LAT_MAX - LAT_MIN), 6),
            "x": round((px + 0.5) / wid * W, 1),
            "z": round((py + 0.5) / hgt * H, 1),
            "ground": round(float(dem[py, px]), 2),
            "threshold": {"underpass": [0.10, 0.20, 0.35], "road": [0.15, 0.30, 0.50],
                          "community": [0.15, 0.30, 0.50], "river": [0.30, 0.60, 1.00]}[typ],
        })
    return sensors


# ---------------------------------------------------------------- 主流程
def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    dem = load_dem()
    print("DEM", dem.shape, "range", round(float(dem.min()), 2), round(float(dem.max()), 2))
    buildings, roads, water_poly, river_lines, green_poly = load_osm()

    bmask, wmask, gmask, rmask = rasterize(dem.shape, buildings, roads, water_poly, river_lines, green_poly)
    # 建筑优先权：建筑内部不画绿地/道路
    landcover = np.zeros(dem.shape, dtype=np.uint8)
    landcover[gmask == 1] = 1
    landcover[rmask == 1] = 2
    landcover[bmask == 1] = 3
    landcover[wmask == 1] = 0
    # 水域最高优先级
    wm = (wmask == 1)
    landcover[wm] = 0

    # 模型网格
    z = resample(dem, GRID_NX, GRID_NY)
    lc = resample_u8(landcover, GRID_NX, GRID_NY)
    z = gaussian_blur(z, 0.8)
    b = (resample_u8((bmask * 255).astype(np.uint8), GRID_NX, GRID_NY) > 110)
    w = (resample_u8((wmask * 255).astype(np.uint8), GRID_NX, GRID_NY) > 90)

    cn = np.full(z.shape, 80.0)
    cn[lc == 1] = 58.0
    cn[lc == 2] = 96.0
    cn[lc == 3] = 94.0
    cn[w] = 100.0
    imperv = np.clip((cn - 55) / 43, 0, 1)

    # 排水能力场（mm/h）：CBD/新建片区较高，老村与下穿段较低，低洼处再折减
    xx = np.linspace(0, 1, GRID_NX)[None, :]
    yy = np.linspace(0, 1, GRID_NY)[:, None]
    cbd = np.exp(-(((xx - 0.30) / 0.16) ** 2 + ((yy - 0.72) / 0.12) ** 2))
    hqb = np.exp(-(((xx - 0.70) / 0.10) ** 2 + ((yy - 0.55) / 0.10) ** 2))
    drain = 30 + 18 * cbd + 6 * hqb
    drain[lc == 1] = 55  # 绿地滞蓄
    drain[lc == 3] = 20  # 建筑屋面径流经立管，地表排水不计
    # 低洼处排水受顶托
    local_low = z < np.percentile(z, 18)
    drain[local_low] *= 0.72
    drain = np.clip(drain, 12, 60)

    # 人口栅格（人/格）：住宅按建筑面积×层数估算
    pop = np.zeros(z.shape)
    for e, xy in buildings:
        t = e["tags"]
        kind = t.get("building", "yes")
        area = poly_area(xy)
        h = estimate_height(t, area, e.get("id"))
        floors = max(1, h / 3.2)
        if kind in ("apartments", "residential", "yes", "dormitory"):
            n = area * floors / 38.0 * 0.85
        elif kind in ("commercial", "office", "retail", "hotel"):
            n = area * floors / 45.0 * 0.35
        else:
            n = area * floors / 60.0 * 0.2
        cx = np.mean([p[0] for p in xy]) / W * GRID_NX
        cy = np.mean([p[1] for p in xy]) / H * GRID_NY
        ix, iy = int(np.clip(cx, 0, GRID_NX - 1)), int(np.clip(cy, 0, GRID_NY - 1))
        pop[iy, ix] += n
    pop = box_blur(pop, 3)

    sensors = build_sensors(dem, bmask, wmask)
    np.savez_compressed(PROCESSED / "grid.npz", z=z.astype(np.float32), lc=lc, cn=cn.astype(np.float32),
                        imperv=imperv.astype(np.float32), b=b, w=w, drain=drain.astype(np.float32),
                        pop=pop.astype(np.float32), W=W, H=H)
    (PROCESSED / "sensors.json").write_text(json.dumps(sensors, ensure_ascii=False, indent=2), encoding="utf-8")
    print("模型网格", z.shape, "高程", round(float(z.min()), 2), round(float(z.max()), 2),
          "人口合计", int(pop.sum()))

    # ---------- 三维地形 ----------
    zr = resample(z, RENDER_NX, RENDER_NY, "bilinear")
    lcr = resample_u8(lc, RENDER_NX, RENDER_NY)
    elev_dm = np.round(zr * 10).astype(np.int16)
    terrain = {
        "nx": RENDER_NX, "ny": RENDER_NY, "w": round(W, 1), "h": round(H, 1),
        "elev": _b64(elev_dm.tobytes()),
        "landcover": _b64(lcr.tobytes()),
        "elevMin": round(float(zr.min()), 2), "elevMax": round(float(zr.max()), 2),
    }
    (WEB_DATA / "terrain.json").write_text(json.dumps(terrain, separators=(",", ":")), encoding="utf-8")

    # ---------- 建筑 ----------
    bld = {"p": [], "h": [], "n": [], "k": [], "b": []}
    for e, xy in buildings:
        t = e["tags"]
        area = poly_area(xy)
        h = estimate_height(t, area, e.get("id"))
        # 量化 0.2m
        flat = []
        for x, zz in xy:
            flat.append(round(x, 1))
            flat.append(round(zz, 1))
        # 基础高程：取多边形内 DEM 的 20 分位，避免悬空
        mask_pts = []
        for i in range(0, len(flat), 2):
            px = int(np.clip(flat[i] / W * dem.shape[1], 0, dem.shape[1] - 1))
            py = int(np.clip(flat[i + 1] / H * dem.shape[0], 0, dem.shape[0] - 1))
            mask_pts.append(dem[py, px])
        base = float(np.percentile(mask_pts, 15)) if mask_pts else 2.0
        kind = t.get("building", "yes")
        bld["p"].append(flat)
        bld["h"].append(round(h, 1))
        bld["n"].append(t.get("name") or t.get("name:zh") or "")
        bld["k"].append(kind)
        bld["b"].append(round(base, 1))
    (WEB_DATA / "buildings.json").write_text(json.dumps(bld, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("建筑导出", len(bld["p"]), "最高", max(bld["h"]))

    # ---------- 道路 / 水系 / 绿地 ----------
    widths = {"motorway": 45, "trunk": 40, "primary": 34, "secondary": 26, "tertiary": 18,
              "residential": 10, "service": 6, "unclassified": 10, "motorway_link": 14,
              "trunk_link": 14, "primary_link": 14, "secondary_link": 12, "tertiary_link": 10,
              "living_street": 8, "road": 8, "track": 4}
    road_out = []
    for e, xy in roads:
        t = e["tags"]
        cls = t.get("highway")
        # 抽稀
        pts = _simplify(xy, 4.0)
        road_out.append({"c": cls, "n": t.get("name", ""), "w": widths.get(cls, 8),
                         "p": [round(v, 1) for p in pts for v in p]})
    water_out, river_out, green_out = [], [], []
    for e, xy in water_poly:
        water_out.append({"n": e["tags"].get("name", ""), "p": [round(v, 1) for p in _simplify(xy, 3.0) for v in p]})
    for e, xy in river_lines:
        river_out.append({"c": e["tags"].get("waterway"), "n": e["tags"].get("name", ""),
                          "w": {"river": 26, "canal": 16, "stream": 8, "ditch": 6}.get(e["tags"].get("waterway"), 8),
                          "p": [round(v, 1) for p in _simplify(xy, 3.0) for v in p]})
    for e, xy in green_poly:
        green_out.append({"n": e["tags"].get("name", ""), "k": e["tags"].get("landuse") or e["tags"].get("leisure") or e["tags"].get("natural", ""),
                          "p": [round(v, 1) for p in _simplify(xy, 3.0) for v in p]})
    vectors = {"roads": road_out, "water": water_out, "rivers": river_out, "green": green_out}
    (WEB_DATA / "vectors.json").write_text(json.dumps(vectors, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("矢量导出 roads", len(road_out), "water", len(water_out), "rivers", len(river_out), "green", len(green_out))

    sensors_path = WEB_DATA / "sensors.json"
    sensors_path.write_text(json.dumps(sensors, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "name": "深澜 · 城市积水风险智慧预警平台",
        "city": "深圳市", "district": "福田区",
        "area": "莲花山—中心公园—福田CBD—华强北",
        "bbox": [LON_MIN, LAT_MIN, LON_MAX, LAT_MAX],
        "center": [(LON_MIN + LON_MAX) / 2, (LAT_MIN + LAT_MAX) / 2],
        "world": [round(W, 1), round(H, 1)],
        "terrain": {"nx": RENDER_NX, "ny": RENDER_NY, "elevMin": round(float(zr.min()), 2), "elevMax": round(float(zr.max()), 2)},
        "model": {"nx": GRID_NX, "ny": GRID_NY, "cell": round(W / GRID_NX, 1)},
        "buildings": len(bld["p"]),
        "sensors": len(sensors),
        "sources": [
            {"name": "Mapzen Terrarium / AWS Open Data", "use": "数字高程模型 DEM", "license": "CC-BY / public"},
            {"name": "OpenStreetMap contributors", "use": "建筑、道路、水系、绿地", "license": "ODbL 1.0"},
            {"name": "Open-Meteo ERA5-Land", "use": "2023-09-07/08 历史小时降雨", "license": "CC-BY 4.0"},
            {"name": "深圳市气象局公开报道", "use": "暴雨过程实况校核", "license": "公开信息"},
        ],
        "generated": "2026-11-17",
    }
    (WEB_DATA / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("完成", WEB_DATA)


def _simplify(pts, tol):
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for p in pts[1:-1]:
        if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) >= tol:
            out.append(p)
    out.append(pts[-1])
    return out


def _b64(b):
    import base64
    return base64.b64encode(b).decode("ascii")


if __name__ == "__main__":
    main()
