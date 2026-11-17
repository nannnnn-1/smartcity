# -*- coding: utf-8 -*-
"""下载 Mapzen Terrarium DEM 瓦片，拼接并裁剪到研究范围。

数据源：AWS Open Data / Mapzen elevation-tiles-prod（Terrarium 编码，全球 30m 级）
编码：elevation = (R * 256 + G + B / 256) - 32768
"""
import math, io, json, time, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
from config import (RAW, PROCESSED, LON_MIN, LON_MAX, LAT_MIN, LAT_MAX,
                    DEM_ZOOM, DEM_URL, M_PER_DEG_LAT, M_PER_DEG_LON)


def deg2num(lat, lon, z):
    lat_r = math.radians(lat)
    n = 2.0 ** z
    return (lon + 180.0) / 360.0 * n, (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n


def num2deg(x, y, z):
    n = 2.0 ** z
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    x0f, y0f = deg2num(LAT_MAX, LON_MIN, DEM_ZOOM)
    x1f, y1f = deg2num(LAT_MIN, LON_MAX, DEM_ZOOM)
    x0, x1 = int(x0f), int(x1f)
    y0, y1 = int(y0f), int(y1f)
    tiles = []
    for ty in range(y0, y1 + 1):
        row = []
        for tx in range(x0, x1 + 1):
            url = DEM_URL.format(z=DEM_ZOOM, x=tx, y=ty)
            path = RAW / f"dem_{DEM_ZOOM}_{tx}_{ty}.png"
            if not path.exists():
                for attempt in range(4):
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "smartcity-course/1.0"})
                        path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
                        break
                    except Exception as e:
                        print("retry", url, e)
                        time.sleep(2 + attempt * 2)
            im = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
            elev = (im[:, :, 0] * 256.0 + im[:, :, 1] + im[:, :, 2] / 256.0) - 32768.0
            row.append(elev)
            print(f"tile z{DEM_ZOOM}/{tx}/{ty}  {elev.shape}  {elev.min():.1f}~{elev.max():.1f} m")
        tiles.append(np.concatenate(row, axis=1))
    mosaic = np.concatenate(tiles, axis=0)
    h, w = mosaic.shape

    # 像素经纬度 -> 在 mosaic 中的裁剪范围
    def xy(lon, lat):
        xf, yf = deg2num(lat, lon, DEM_ZOOM)
        return (xf - x0) * 256.0, (yf - y0) * 256.0
    px0, py0 = xy(LON_MIN, LAT_MAX)
    px1, py1 = xy(LON_MAX, LAT_MIN)
    crop = mosaic[int(py0):int(py1), int(px0):int(px1)]
    np.save(RAW / "dem_crop.npy", crop)
    meta = {
        "source": "Mapzen Terrarium / AWS Open Data (SRTM+GMTED+ETOPO)",
        "zoom": DEM_ZOOM,
        "crop_px": [int(px0), int(py0), int(px1), int(py1)],
        "shape": list(crop.shape),
        "elev_min": float(crop.min()), "elev_max": float(crop.max()),
        "resolution_m": 156543.03392 * math.cos(math.radians((LAT_MIN + LAT_MAX) / 2)) / (2 ** DEM_ZOOM),
        "bbox": [LON_MIN, LAT_MIN, LON_MAX, LAT_MAX],
        "note": "Terrarium: elev = R*256 + G + B/256 - 32768",
    }
    (RAW / "dem_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print("DEM 裁剪完成", crop.shape, "高度范围", crop.min(), crop.max())


if __name__ == "__main__":
    main()
