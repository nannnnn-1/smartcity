# -*- coding: utf-8 -*-
"""下载深圳福田 2023-09-07/08 历史小时降雨（Open-Meteo ERA5-Land 再分析）。

同时生成设计暴雨（芝加哥雨型）参数，供情景模拟使用。
"""
import json, urllib.request
from config import RAW, RAIN_LAT, RAIN_LON

URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
       "&start_date=2023-09-06&end_date=2023-09-10&hourly=precipitation,rain"
       "&timezone=Asia%2FShanghai")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL.format(lat=RAIN_LAT, lon=RAIN_LON),
                                 headers={"User-Agent": "smartcity-course/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=60).read())
    out = RAW / "rainfall_202309.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    times = data["hourly"]["time"]
    p = data["hourly"]["precipitation"]
    peak = max(range(len(p)), key=lambda i: p[i] or 0)
    print("小时数", len(times), "累计", round(sum(x or 0 for x in p), 1), "mm")
    print("峰值", times[peak], p[peak], "mm/h")
    print("9/7 00:00 - 9/9 00:00:")
    for t, v in zip(times, p):
        if "2023-09-07" in t or "2023-09-08" in t:
            print(t, v)


if __name__ == "__main__":
    main()
