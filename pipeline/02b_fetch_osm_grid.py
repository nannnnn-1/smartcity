# -*- coding: utf-8 -*-
"""OSM Map API 分块抓取（Overpass 不可用时的回退方案）。

OSM Map API 限制：bbox 面积 <= 0.25 平方度。研究区 0.06x0.039=0.0023，
理论上一次可取，但单次节点数受限，故按 4x3 分块并发抓取并合并。
"""
import json, time, math, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET
from config import RAW, LON_MIN, LON_MAX, LAT_MIN, LAT_MAX

NX, NY = 4, 3
OUT = RAW / "osm_elements.json"


def fetch_tile(args):
    ix, iy = args
    lon0 = LON_MIN + (LON_MAX - LON_MIN) * ix / NX
    lon1 = LON_MIN + (LON_MAX - LON_MIN) * (ix + 1) / NX
    lat0 = LAT_MIN + (LAT_MAX - LAT_MIN) * iy / NY
    lat1 = LAT_MIN + (LAT_MAX - LAT_MIN) * (iy + 1) / NY
    # 略微外扩，避免边界处几何断裂
    pad = 0.0006
    url = (f"https://api.openstreetmap.org/api/0.6/map?bbox="
           f"{lon0-pad:.6f},{lat0-pad:.6f},{lon1+pad:.6f},{lat1+pad:.6f}")
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "smartcity-course/1.0 (Futian flood study)"})
            t = time.time()
            data = urllib.request.urlopen(req, timeout=240).read()
            root = ET.fromstring(data)
            nodes = {nd.get("id"): (float(nd.get("lon")), float(nd.get("lat"))) for nd in root.findall("node")}
            ways = []
            for wy in root.findall("way"):
                tags = {tg.get("k"): tg.get("v") for tg in wy.findall("tag")}
                nds = [nd.get("ref") for nd in wy.findall("nd")]
                ways.append({"id": wy.get("id"), "tags": tags, "nodes": nds})
            print(f"tile {ix},{iy}: {len(data)/1e6:.2f} MB nodes={len(nodes)} ways={len(ways)} {time.time()-t:.1f}s", flush=True)
            return nodes, ways
        except Exception as e:
            print(f"tile {ix},{iy} retry {attempt}: {repr(e)[:160]}", flush=True)
            time.sleep(2 + attempt * 3)
    return {}, []


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    all_nodes, all_ways = {}, {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(fetch_tile, (ix, iy)): (ix, iy) for iy in range(NY) for ix in range(NX)}
        for f in as_completed(futs):
            nodes, ways = f.result()
            all_nodes.update(nodes)
            for w in ways:
                all_ways[w["id"]] = w
    # 只保留节点齐全的 way
    out_ways = []
    for w in all_ways.values():
        if all(n in all_nodes for n in w["nodes"]):
            out_ways.append(w)
    data = {"nodes": all_nodes, "ways": out_ways}
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print("保存", OUT, f"{OUT.stat().st_size/1e6:.1f} MB", "nodes", len(all_nodes), "ways", len(out_ways))


if __name__ == "__main__":
    main()
