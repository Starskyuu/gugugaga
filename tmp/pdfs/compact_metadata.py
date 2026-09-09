from pathlib import Path
import json,re,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
items=json.loads(Path(r"F:\gugugaga\tmp\pdfs\papers_index.json").read_text(encoding="utf-8"))
for i,x in enumerate(items,1):
    h=x.get("head","")
    dois=[]
    for m in re.findall(r"10\.\d{4,9}\s*/\s*[-._;()/:A-Za-z0-9]+",h,re.I):
        d=re.sub(r"\s+","",m).rstrip(".);,]")
        if d not in dois:dois.append(d)
    title=x.get("title","")
    author=x.get("author","")
    years=", ".join(x.get("year_hits",[])[:4])
    print(f"[{i:02d}] {x['file']}\n META title={title} | author={author} | years={years} | DOI={'; '.join(dois[:3])}\n HEAD {h[:850]}\n")
