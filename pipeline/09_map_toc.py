import re,json
from pypdf import PdfReader
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
md=open(ROOT/"docs/设计报告.md",encoding="utf-8").read().splitlines()
heads=[]
in_code=False
for line in md:
    if line.startswith("```"):
        in_code=not in_code; continue
    if in_code: continue
    if line.startswith("### "): heads.append(line[4:].strip())
    elif line.startswith("## "): heads.append(line[3:].strip())
r=PdfReader(ROOT/"docs/设计报告.pdf")
pages=[re.sub(r"\s+","",p.extract_text() or "") for p in r.pages]
print("pages",len(pages))
# body starts after TOC; find abstract body marker
body_start=next(i for i,t in enumerate(pages) if "城市内涝是极端天气下最直接" in t)
print("body_start",body_start+1)
res={}; missing=[]
for h in heads:
    key=re.sub(r"\s+","",h)
    idx=None
    for i in range(body_start,len(pages)):
        if key in pages[i]:
            idx=i; break
    if idx is None:
        # 尝试前 10 字
        k2=key[:10]
        for i in range(body_start,len(pages)):
            if k2 in pages[i]: idx=i; break
    if idx is None: missing.append(h)
    else: res[h]=idx+1
json.dump(res,open(ROOT/"docs/toc_pages.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("mapped",len(res),"missing",missing)
for h in heads[:12]: print(h,res.get(h))
