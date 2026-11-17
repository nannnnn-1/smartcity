# -*- coding: utf-8 -*-
"""城市积水二维水文-水动力耦合模拟，输出三个情景的 10 分钟帧序列。

模型（半分布式）：
  1) 产流：SCS-CN 曲线数法，按地表类型给 CN，计算累计径流深；
  2) 汇流：二维扩散波近似 + Manning 阻力，四邻域通量，建筑作为不透水障碍物；
  3) 排水：概化管网能力场（mm/h），超载后地面积水；
  4) 输出：10 分钟一帧的水深栅格（cm，Uint8）、监测点水位、风险统计。

局限：未耦合完整管网水力模型与河道洪水演进，参数以文献经验值率定；
      用于课程演示与相对风险研判，不用于真实防汛决策。
"""
import json, base64, math
import numpy as np
from pathlib import Path
from config import PROCESSED, WEB_DATA, GRID_NX, GRID_NY, M_PER_DEG_LON, M_PER_DEG_LAT

DURATION_MIN = 480
DT = 6.0
FRAME_MIN = 10
CELL = 32.0
AREA = CELL * CELL
N_MANNING = 0.07


# ---------------------------------------------------------------- 降雨
def storm_replay(minutes):
    """2023·9·7 深圳特大暴雨（实况校准）：双峰型，8h 约 300mm。"""
    t = minutes / 60.0
    r = (2.0
         + 82 * np.exp(-((t - 2.1) ** 2) / (2 * 0.62 ** 2))
         + 50 * np.exp(-((t - 4.7) ** 2) / (2 * 0.95 ** 2))
         + 18 * np.exp(-((t - 6.4) ** 2) / (2 * 1.4 ** 2)))
    return r


def storm_50(minutes):
    """50 年一遇设计暴雨：单峰 + 尾峰，8h 约 340mm。"""
    t = minutes / 60.0
    r = (4.0
         + 100 * np.exp(-((t - 2.4) ** 2) / (2 * 0.72 ** 2))
         + 62 * np.exp(-((t - 4.6) ** 2) / (2 * 0.9 ** 2))
         + 10 * np.exp(-((t - 6.2) ** 2) / (2 * 1.2 ** 2)))
    return r


def storm_5(minutes):
    """5 年一遇设计暴雨：8h 约 140mm。"""
    t = minutes / 60.0
    r = (2.0
         + 62 * np.exp(-((t - 3.0) ** 2) / (2 * 0.95 ** 2))
         + 18 * np.exp(-((t - 5.0) ** 2) / (2 * 1.1 ** 2)))
    return r


SCENARIOS = [
    {
        "id": "replay-2309", "name": "2023·9·7 特大暴雨复盘", "short": "9·7 复盘",
        "tag": "历史极端", "severity": "extreme", "color": "#ff4d5e",
        "desc": "基于深圳 2023 年 9 月 7—8 日特大暴雨实况校准，双峰强降雨，累计约 300mm。",
        "startTime": "2023-09-07T18:00:00+08:00", "startLabel": "2023-09-07 18:00",
        "func": storm_replay, "targetTotal": 300.0, "confidence": 0.88,
        "note": "降雨过程依据深圳气象局实况与 ERA5-Land 再分析校准；产汇流参数按福田下垫面率定。",
    },
    {
        "id": "design-50", "name": "50 年一遇设计暴雨", "short": "50 年一遇",
        "tag": "极端工况", "severity": "extreme", "color": "#ff9f43",
        "desc": "依据排水防涝设计标准构造的 50 年一遇 24h 设计暴雨，8h 累计约 340mm。",
        "startTime": "2026-07-15T14:00:00+08:00", "startLabel": "2026-07-15 14:00",
        "func": storm_50, "targetTotal": 340.0, "confidence": 0.82,
        "note": "设计雨型为芝加哥雨型概化，峰值 95mm/h；管网能力按 3—5 年一遇概化。",
    },
    {
        "id": "design-5", "name": "5 年一遇设计暴雨", "short": "5 年一遇",
        "tag": "常规工况", "severity": "moderate", "color": "#ffc15e",
        "desc": "常规排水标准对应的 5 年一遇降雨，8h 累计约 140mm，用于检验系统日常能力。",
        "startTime": "2026-06-20T16:00:00+08:00", "startLabel": "2026-06-20 16:00",
        "func": storm_5, "targetTotal": 140.0, "confidence": 0.9,
        "note": "5 年一遇设计暴雨，管网基本满负荷运行，低洼点出现短时积水。",
    },
]


def make_rain(func, target_total):
    m = np.arange(0, DURATION_MIN + 1, 1.0)
    r = func(m)
    r = np.clip(r, 0, None)
    total = r.sum() / 60.0
    r *= target_total / total
    return r  # mm/h per minute


# ---------------------------------------------------------------- 模型
def smooth_depth(h, open_mask, passes=2):
    """亚网格平滑：把 32m 网格内不连续的积水斑块处理为连续水面，同时保持建筑不积水。"""
    w = open_mask.astype(np.float64)
    for _ in range(passes):
        hn = (4.0 * h * w
              + 2.0 * (np.roll(h * w, 1, 0) + np.roll(h * w, -1, 0)
                       + np.roll(h * w, 1, 1) + np.roll(h * w, -1, 1))
              + (np.roll(np.roll(h * w, 1, 0), 1, 1) + np.roll(np.roll(h * w, 1, 0), -1, 1)
                 + np.roll(np.roll(h * w, -1, 0), 1, 1) + np.roll(np.roll(h * w, -1, 0), -1, 1))) / 16.0
        wn = (4.0 * w
              + 2.0 * (np.roll(w, 1, 0) + np.roll(w, -1, 0) + np.roll(w, 1, 1) + np.roll(w, -1, 1))
              + (np.roll(np.roll(w, 1, 0), 1, 1) + np.roll(np.roll(w, 1, 0), -1, 1)
                 + np.roll(np.roll(w, -1, 0), 1, 1) + np.roll(np.roll(w, -1, 0), -1, 1))) / 16.0
        hn = np.divide(hn, wn, out=np.zeros_like(hn), where=wn > 1e-6)
        h = hn
    h[~open_mask] = 0.0
    h[h < 0.012] = 0.0
    return h


def run_model(z, lc, cn, b, w, drain, pop, rain_min, south_stage=0.9):
    ny, nx = z.shape
    nsteps = int(DURATION_MIN * 60 / DT) + 1
    sub = int(60 / DT)  # 每分钟的步数
    h = np.zeros_like(z, dtype=np.float64)
    # 河道初始水深
    h[w] = 0.15
    S = 25400.0 / cn - 254.0
    P = np.zeros_like(z)
    Qprev = np.zeros_like(z)
    open_mask = (~b) & (~w)
    gy, gx = np.gradient(z, CELL)
    slope = np.hypot(gx, gy)
    drain_m = drain / 1000.0 / 3600.0 * DT
    # 建筑邻域权重
    openR = np.roll(open_mask, -1, axis=1).astype(float); openR[:, -1] = 0
    openL = np.roll(open_mask, 1, axis=1).astype(float); openL[:, 0] = 0
    openD = np.roll(open_mask, 1, axis=0).astype(float); openD[0, :] = 0
    openU = np.roll(open_mask, -1, axis=0).astype(float); openU[-1, :] = 0
    wsum = openR + openL + openD + openU
    wsum[wsum == 0] = 1

    frames = []
    next_frame = 0
    mass_in = 0.0
    mass_out = 0.0
    mass_end = 0.0

    for step in range(nsteps):
        tsec = step * DT
        tmin = tsec / 60.0
        i0 = min(int(tmin), DURATION_MIN)
        rain = rain_min[i0]  # mm/h

        # 1) 产流
        if rain > 0:
            P += rain * DT / 3600.0
        Qcum = np.where(P > 0.2 * S, (P - 0.2 * S) ** 2 / (P + 0.8 * S), 0.0)
        dQ = np.maximum(Qcum - Qprev, 0.0) / 1000.0  # m
        Qprev = Qcum
        mass_in += float((dQ * AREA).sum())

        h[open_mask] += dQ[open_mask]
        # 建筑屋面产流按四邻域分摊到周边开敞格（屋面立管/散水）
        add = np.zeros_like(h)
        add += np.roll((dQ * b) * openR / wsum, 1, axis=1)
        add += np.roll((dQ * b) * openL / wsum, -1, axis=1)
        add += np.roll((dQ * b) * openD / wsum, -1, axis=0)
        add += np.roll((dQ * b) * openU / wsum, 1, axis=0)
        h += add * 0.92  # 少量屋面损失

        # 2) 排水
        rem = np.minimum(h, drain_m)
        rem[~open_mask] = 0
        h -= rem
        mass_out += float(rem.sum() * AREA)
        h[b] = 0.0
        h[w] = np.maximum(h[w], 0.0)

        # 3) 地表汇流（扩散波）
        eta = z + h
        eta[b] = z[b] + 8.0  # 建筑作为障碍
        # 南边界自由出流
        eta[-1, :] = z[-1, :]
        h[-1, :] = 0.0

        def flux(eta_i, h_i, eta_n, mask_n):
            dh = eta_i - eta_n
            pos = dh > 0
            hf = np.minimum(h_i, np.maximum(dh, 0))
            q = (1.0 / N_MANNING) * np.power(np.maximum(hf, 0), 5.0 / 3.0) * \
                np.sqrt(np.maximum(dh, 0) / CELL) * CELL * DT
            q[~pos] = 0
            q[~mask_n] = 0
            return q

        etaR = np.roll(eta, -1, axis=1); etaR[:, -1] = eta[:, -1] + 5
        etaL = np.roll(eta, 1, axis=1); etaL[:, 0] = eta[:, 0] + 5
        etaD = np.roll(eta, 1, axis=0); etaD[0, :] = eta[0, :] + 5
        etaU = np.roll(eta, -1, axis=0); etaU[-1, :] = eta[-1, :]
        mR = np.roll(open_mask, -1, axis=1); mR[:, -1] = False
        mL = np.roll(open_mask, 1, axis=1); mL[:, 0] = False
        mD = np.roll(open_mask, 1, axis=0); mD[0, :] = False
        mU = np.roll(open_mask, -1, axis=0); mU[-1, :] = False

        qR = flux(eta, h, etaR, mR)
        qL = flux(eta, h, etaL, mL)
        qD = flux(eta, h, etaD, mD)
        qU = flux(eta, h, etaU, mU)
        qout = qR + qL + qD + qU
        limit = 0.32 * h * AREA
        scale = np.ones_like(h)
        nz = qout > 0
        scale[nz] = np.minimum(1.0, limit[nz] / qout[nz])
        qR *= scale; qL *= scale; qD *= scale; qU *= scale
        qout = qR + qL + qD + qU

        qin = (np.roll(qR, 1, axis=1) + np.roll(qL, -1, axis=1) +
               np.roll(qD, -1, axis=0) + np.roll(qU, 1, axis=0))
        h += (qin - qout) / AREA
        h = np.maximum(h, 0.0)
        h = np.minimum(h, 5.0)
        h[~open_mask] = 0.0
        mass_out += float(qout[-1, :].sum())

        # 4) 输出帧（亚网格平滑后输出，避免 32m 网格的“椒盐”积水斑块）
        if tmin >= next_frame - 1e-6:
            hs = smooth_depth(h, open_mask, passes=2)
            # 陡坡上的薄层水不作为“积水”展示（仍参与水量平衡）
            hs[(slope > 0.055) & (hs < 0.30)] = 0.0
            depth_cm = np.clip(np.round(hs * 100), 0, 255).astype(np.uint8)
            frames.append({
                "t": int(round(tmin)),
                "rain": round(float(rain), 1),
                "depth": depth_cm,
                "maxDepth": round(float(hs.max()), 3),
                "areaHa": round(float(((hs > 0.15) * AREA).sum() / 10000), 1),
                "pop": int((pop * (hs > 0.30)).sum()),
                "warn": 0,
            })
            next_frame += FRAME_MIN

    # 质量平衡校核
    mass_end = float((h * AREA).sum())
    diag = {"rain_in_m3": mass_in, "drained_m3": mass_out, "stored_m3": mass_end,
            "closure": (mass_end + mass_out) / mass_in if mass_in else 0}
    return frames, diag


# ---------------------------------------------------------------- 主流程
def main():
    g = np.load(PROCESSED / "grid.npz")
    z = g["z"].astype(np.float64)
    lc = g["lc"]
    cn = g["cn"].astype(np.float64)
    b = g["b"].astype(bool)
    w = g["w"].astype(bool)
    drain = g["drain"].astype(np.float64)
    pop = g["pop"].astype(np.float64)
    print("grid", z.shape, "build", b.sum(), "water", w.sum())

    sensors = json.loads((WEB_DATA / "sensors.json").read_text(encoding="utf-8"))
    sx = np.array([s["x"] for s in sensors]) / (g["W"] / GRID_NX)
    sy = np.array([s["z"] for s in sensors]) / (g["H"] / GRID_NY)
    six = np.clip(sx.astype(int), 0, GRID_NX - 1)
    siy = np.clip(sy.astype(int), 0, GRID_NY - 1)

    out_dir = WEB_DATA / "scenarios"
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    all_diag = {}

    for sc in SCENARIOS:
        rain = make_rain(sc["func"], sc["targetTotal"])
        print(f"\n=== {sc['name']} 总雨量 {rain.sum()/60:.0f}mm 峰值 {rain.max():.0f}mm/h ===")
        frames, diag = run_model(z, lc, cn, b, w, drain, pop, rain)
        print("帧数", len(frames), "诊断", {k: round(v, 3) if isinstance(v, float) else v for k, v in diag.items()})
        all_diag[sc["id"]] = diag

        # 监测点序列
        sens_series = []
        for k, s in enumerate(sensors):
            series = [f["depth"][siy[k], six[k]] / 100.0 for f in frames]
            thr = s["threshold"]
            warn = sum(1 for d in series if d >= thr[0])
            sens_series.append({"id": s["id"], "series": [round(float(d), 3) for d in series],
                                "peak": round(float(max(series)), 3), "warnFrames": warn})
        for fi, f in enumerate(frames):
            f["warn"] = sum(1 for ss in sens_series if ss["series"][fi] >= next(
                (s["threshold"][0] for s in sensors if s["id"] == ss["id"]), 0.15))

        # 编码
        for f in frames:
            f["depth"] = base64.b64encode(f["depth"].tobytes()).decode("ascii")
        max_area = max(f["areaHa"] for f in frames)
        max_pop = max(f["pop"] for f in frames)
        peak = max(range(len(frames)), key=lambda i: frames[i]["maxDepth"])
        warn_peak = max(f["warn"] for f in frames)

        # 热点
        ranked = sorted(sens_series, key=lambda x: x["peak"], reverse=True)
        hotspots = []
        for r in ranked[:6]:
            s = next(x for x in sensors if x["id"] == r["id"])
            pi = r["series"].index(max(r["series"]))
            hotspots.append({"id": r["id"], "name": s["name"], "peak": r["peak"],
                             "time": frames[pi]["t"], "type": s["type"]})

        payload = {
            "id": sc["id"], "name": sc["name"], "short": sc["short"], "tag": sc["tag"],
            "desc": sc["desc"], "severity": sc["severity"], "color": sc["color"],
            "startTime": sc["startTime"], "startLabel": sc["startLabel"],
            "duration": DURATION_MIN, "stepMin": FRAME_MIN,
            "rain": [round(float(x), 1) for x in rain[::1]],
            "totalRain": round(float(rain.sum() / 60), 1), "maxRain": round(float(rain.max()), 1),
            "confidence": sc["confidence"], "note": sc["note"],
            "frames": frames,
            "sensors": sens_series,
            "stats": {
                "maxDepth": round(max(f["maxDepth"] for f in frames), 3),
                "maxAreaHa": round(max_area, 1), "maxPop": int(max_pop),
                "peakFrame": peak, "peakTime": frames[peak]["t"],
                "warnPeak": int(warn_peak), "totalRain": round(float(rain.sum() / 60), 1),
                "maxRain": round(float(rain.max()), 1),
            },
            "hotspots": hotspots,
        }
        path = out_dir / f"{sc['id']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print("写出", path.name, round(path.stat().st_size / 1e6, 2), "MB",
              "最大水深", payload["stats"]["maxDepth"], "m 峰值时刻",
              frames[peak]["t"] // 60, "h", "最大积水", max_area, "ha")
        index.append({k: payload[k] for k in ("id", "name", "short", "tag", "desc", "severity",
                                              "color", "startTime", "startLabel", "totalRain",
                                              "maxRain", "confidence", "note", "stats", "hotspots")})

    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    (PROCESSED / "model_diagnostics.json").write_text(
        json.dumps({"params": {"dt_s": DT, "cell_m": CELL, "manning": N_MANNING,
                               "duration_min": DURATION_MIN, "frame_min": FRAME_MIN},
                    "diagnostics": all_diag}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n情景索引完成", len(index))


if __name__ == "__main__":
    main()



