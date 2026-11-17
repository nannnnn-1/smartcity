# -*- coding: utf-8 -*-
"""监测点选址校准：将 16 个候选点吸附到 400m 范围内积水最深的开敞网格。

真实积水监测点通常布设在历史易涝点、下穿隧道最低点。这里用 50 年一遇情景
的 max-depth 包络面做一次“模型辅助选址”，保证演示系统中每个点位都有明确的
物理含义，而不是随机撒点。
"""
import json, base64
import numpy as np
from config import PROCESSED, WEB_DATA, GRID_NX, GRID_NY

STREET_THR = {
    "SN-01": ("香蜜湖街道", [30, 40, 70]),
    "SN-02": ("福保街道", [40, 45, 80]),
    "SN-03": ("福田街道", [30, 50, 80]),
    "SN-04": ("福田街道", [30, 50, 80]),
    "SN-05": ("华富街道", [35, 45, 80]),
    "SN-06": ("华强北街道", [40, 65, 100]),
    "SN-07": ("园岭街道", [35, 45, 80]),
    "SN-08": ("莲花街道", [40, 45, 65]),
    "SN-09": ("莲花街道", [40, 45, 65]),
    "SN-10": ("香蜜湖街道", [30, 40, 70]),
    "SN-11": ("福保街道", [40, 45, 80]),
    "SN-12": ("梅林街道", [30, 45, 70]),
    "SN-13": ("华富街道", [35, 45, 80]),
    "SN-14": ("福田街道", [30, 50, 80]),
    "SN-15": ("华强北街道", [40, 65, 100]),
    "SN-16": ("莲花街道", [40, 45, 65]),
}


def main():
    g = np.load(PROCESSED / "grid.npz")
    z = g["z"]; b = g["b"]; w = g["w"]; W = float(g["W"]); H = float(g["H"])
    d = json.load(open(WEB_DATA / "scenarios" / "design-50.json", encoding="utf-8"))
    env = np.zeros((GRID_NY, GRID_NX), dtype=np.float32)
    for f in d["frames"]:
        a = np.frombuffer(base64.b64decode(f["depth"]), np.uint8).reshape(GRID_NY, GRID_NX)
        env = np.maximum(env, a)
    sensors = json.load(open(WEB_DATA / "sensors.json", encoding="utf-8"))
    used = []
    for s in sensors:
        cx = int(np.clip(s["x"] / (W / GRID_NX), 0, GRID_NX - 1))
        cy = int(np.clip(s["z"] / (H / GRID_NY), 0, GRID_NY - 1))
        cands = []
        for dy in range(-12, 13):
            for dx in range(-12, 13):
                x, y = cx + dx, cy + dy
                if 0 <= x < GRID_NX and 0 <= y < GRID_NY and not b[y, x] and not w[y, x]:
                    cands.append((float(env[y, x]), dx, dy, x, y))
        cands.sort(reverse=True)
        pick = None
        for v, dx, dy, x, y in cands:
            if all((x - ux) ** 2 + (y - uy) ** 2 >= 9 for ux, uy in used):
                pick = (v, dx, dy, x, y)
                break
        if pick is None:
            pick = cands[0]
        v, dx, dy, nx, ny = pick
        used.append((nx, ny))
        s["x"] = round((nx + 0.5) * W / GRID_NX, 1)
        s["z"] = round((ny + 0.5) * H / GRID_NY, 1)
        s["ground"] = round(float(z[ny, nx]), 2)
        s["lon"] = round(s["lon"] + dx * (114.100 - 114.040) / GRID_NX, 6)
        s["lat"] = round(s["lat"] - dy * (22.572 - 22.533) / GRID_NY, 6)
        s["calibrated"] = True
        street, thr = STREET_THR[s["id"]]
        s["street"] = street
        s["rainThreshold"] = thr
        print(s["id"], s["name"], "-> cell", nx, ny, "peak", round(float(v) / 100, 2), "m",
              "ground", s["ground"])
    for p in (WEB_DATA / "sensors.json", PROCESSED / "sensors.json"):
        p.write_text(json.dumps(sensors, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已更新", WEB_DATA / "sensors.json")


if __name__ == "__main__":
    main()

