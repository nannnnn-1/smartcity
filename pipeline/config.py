# -*- coding: utf-8 -*-
"""项目全局配置：研究范围、坐标系与数据源参数。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
WEB_DATA = ROOT / "system" / "public" / "data"

# 研究范围（深圳福田：莲花山—中心公园—福田CBD—华强北）
LON_MIN, LON_MAX = 114.040, 114.100
LAT_MIN, LAT_MAX = 22.533, 22.572
CENTER_LON = (LON_MIN + LON_MAX) / 2
CENTER_LAT = (LAT_MIN + LAT_MAX) / 2

# WGS84 近似换算（深圳纬度）
M_PER_DEG_LAT = 110852.0
M_PER_DEG_LON = 111320.0 * 0.92455  # cos(22.55°)

# 地形瓦片（Mapzen Terrarium，AWS Open Data）
DEM_ZOOM = 15
DEM_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

# Open-Meteo 历史再分析（ERA5-Land）
RAIN_LAT, RAIN_LON = 22.5525, 114.0700

# 模拟网格（水文模型）
GRID_NX, GRID_NY = 192, 136          # 约 32 m / 格
RENDER_NX, RENDER_NY = 256, 184      # 渲染地形网格
