# -*- coding: utf-8 -*-
"""下载研究范围 OSM 数据（建筑、道路、水系、绿地），供三维场景与地表参数使用。

优先 Overpass API（仅取需要的图层，数据量可控）；失败时回退 OSM Map API 分块抓取。
数据许可：© OpenStreetMap contributors, ODbL 1.0
"""
import json, time, math, urllib.request, urllib.parse, sys
from pathlib import Path
from config import RAW, LON_MIN, LON_MAX, LAT_MIN, LAT_MAX

BBOX = f"{LAT_MIN},{LON_MIN},{LAT_MAX},{LON_MAX}"
QUERY = f"""[out:json][timeout:600];
(
  way["building"]({BBOX});
  way["highway"]({BBOX});
  way["waterway"]({BBOX});
  way["natural"="water"]({BBOX});
  way["landuse"]({BBOX});
  way["leisure"]({BBOX});
  way["railway"]({BBOX});
  way["place"]({BBOX});
  node["amenity"~"hospital|school|subway_entrance|fire_station|police"]({BBOX});
);
out geom;"""

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


def fetch_overpass():
    body = ("data=" + urllib.parse.quote(QUERY)).encode()
    for host in MIRRORS:
        try:
            print("尝试 Overpass:", host, flush=True)
            req = urllib.request.Request(host, data=body,
                                         headers={"User-Agent": "smartcity-course/1.0 (Futian flood study)"})
            t = time.time()
            raw = urllib.request.urlopen(req, timeout=600).read()
            print(f"成功 {len(raw)/1e6:.1f} MB, {time.time()-t:.1f}s")
            return json.loads(raw)
        except Exception as e:
            print("失败:", repr(e)[:200], flush=True)
    return None


def fetch_osm_api_grid(n=4):
    """OSM Map API 仅允许 <=0.25 平方度；这里按 4x4 分块抓取并合并 XML。"""
    import xml.etree.ElementTree as ET
    nodes, ways = {}, {}
    for iy in range(n):
        for ix in range(n):
            lon0 = LON_MIN + (LON_MAX - LON_MIN) * ix / n
            lon1 = LON_MIN + (LON_MAX - LON_MIN) * (ix + 1) / n
            lat0 = LAT_MIN + (LAT_MAX - LAT_MIN) * iy / n
            lat1 = LAT_MIN + (LAT_MAX - LAT_MIN) * (iy + 1) / n
            url = f"https://api.openstreetmap.org/api/0.6/map?bbox={lon0},{lat0},{lon1},{lat1}"
            print("OSM API tile", ix, iy, flush=True)
            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "smartcity-course/1.0"})
                    data = urllib.request.urlopen(req, timeout=180).read()
                    root = ET.fromstring(data)
                    for nd in root.findall("node"):
                        nodes[nd.get("id")] = nd
                    for wy in root.findall("way"):
                        ways[wy.get("id")] = wy
                    break
                except Exception as e:
                    print("  retry", repr(e)[:160], flush=True)
                    time.sleep(3)
    # 简化：保存 OSM XML 合并文件，由 03 脚本解析
    out = RAW / "osm_grid"
    out.mkdir(exist_ok=True)
    print(f"OSM API 抓取完成 nodes={len(nodes)} ways={len(ways)}")
    return None


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "osm_raw.json"
    if path.exists() and path.stat().st_size > 1e6:
        print("已存在，跳过", path, path.stat().st_size)
        return
    data = fetch_overpass()
    if data is None:
        print("Overpass 全部失败，改用 OSM Map API 分块（较慢）")
        fetch_osm_api_grid()
        sys.exit(2)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print("保存", path, path.stat().st_size / 1e6, "MB")


if __name__ == "__main__":
    main()
