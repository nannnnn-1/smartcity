# -*- coding: utf-8 -*-
"""生成 3 分钟演示视频的中文旁白（Windows SAPI），并输出分段时长。"""
import subprocess, wave, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "video"
OUT.mkdir(exist_ok=True)

SEGS = [
    ("01", "城市内涝，是极端暴雨下最危险的分钟级战场。二零二三年九月七日，深圳福田平均降雨二百六十三点八毫米。我们做的，是把这场雨，装进一个可推演的三维数字孪生。"),
    ("02", "问题不只是看不到，更是算不清。我们坚持数据先行：五米DEM、三千八百七十一栋建筑、三千一百零八条道路、ERA5降雨，以及深圳官方街道阈值。先把二十六点七平方公里的数字底座搭好，再谈系统。"),
    ("03", "管网和逐点易涝点没有公开，我们不伪造。用SCS-CN产流、二维扩散波汇流、概化排水能力场，输出九月七日、五十年一遇、五年一遇三套情景。每十分钟一帧，共四十九帧。"),
    ("04", "五十年一遇是最不利工况：最大水深二点三三米，积水二百九十九公顷，五点八万人受影响。九月七日复盘是双峰雨型，退水之后还会再涨；五年一遇，只有低洼点短时积水。"),
    ("05", "三维不是贴图。地形有等高线，建筑是真实轮廓，水面跟着地形起伏，雨幕跟随相机。四万七千个地形顶点、三千八百七十一栋建筑合并绘制，保证流畅。"),
    ("06", "预警分五级，下穿隧道阈值自动下调。点开任何一个监测点，能看到四十九帧过程线、街道雨量阈值和处置建议。P零封闭抽排，P一预置，P二巡查，P三常态。"),
    ("07", "系统已经完成百分之八十：数据、模型、三维、预警、处置，全链路可运行。剩下百分之二十，按四条线分给四个人：数据模型、三维前端、平台集成、产品表达。深澜，让正确的人，在正确的时间，去到正确的地点。"),
]


def synth():
    ps = r'''
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice("Microsoft Huihui Desktop")
$s.Rate = 0
'''
    for sid, text in SEGS:
        path = OUT / f"nar_{sid}.wav"
        ps += f'$s.SetOutputToWaveFile("{path}")\n$s.Speak("{text}")\n$s.SetOutputToNull()\n'
    ps += '$s.Dispose()\n'
    p = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True, encoding="utf-8")
    print(p.stdout, p.stderr)
    total = 0
    info = []
    for sid, _ in SEGS:
        path = OUT / f"nar_{sid}.wav"
        with wave.open(str(path), "rb") as w:
            d = w.getnframes() / w.getframerate()
        total += d
        info.append((sid, round(d, 2)))
    print(info, "total", round(total, 2))
    (OUT / "narration.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")


def concat():
    # 统一为 16k/16bit 单声道，段间加 0.45s 静音
    import numpy as np
    rate = 16000
    chunks = []
    for sid, _ in SEGS:
        with wave.open(str(OUT / f"nar_{sid}.wav"), "rb") as w:
            n = w.getnframes()
            data = w.readframes(n)
            arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            if w.getnchannels() == 2:
                arr = arr.reshape(-1, 2).mean(axis=1)
            # 重采样（SAPI 通常已是 16k；若不是则线性插值）
            if w.getframerate() != rate:
                x = np.linspace(0, len(arr) - 1, int(len(arr) * rate / w.getframerate()))
                arr = np.interp(x, np.arange(len(arr)), arr)
            chunks.append(arr.astype(np.int16))
            chunks.append(np.zeros(int(rate * 0.45), dtype=np.int16))
    out = np.concatenate(chunks)
    with wave.open(str(OUT / "narration.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(out.tobytes())
    print("narration", len(out) / rate, "s")


if __name__ == "__main__":
    synth()
    concat()
