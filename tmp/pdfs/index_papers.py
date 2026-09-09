from pathlib import Path
import json, re
from pypdf import PdfReader

src = Path(r"F:\gugugaga\01 papers")
out = Path(r"F:\gugugaga\tmp\pdfs\papers_index.json")
items=[]
for p in sorted(src.rglob("*.pdf"), key=lambda x:x.name.lower()):
    try:
        r=PdfReader(str(p), strict=False)
        meta=r.metadata or {}
        pages=[]
        for pg in r.pages:
            try: pages.append(pg.extract_text() or "")
            except Exception: pages.append("")
        full="\n".join(pages)
        clean=re.sub(r"\s+"," ",full).strip()
        def window(patterns, n=3500):
            for pat in patterns:
                m=re.search(pat, clean, re.I)
                if m:return clean[m.start():m.start()+n]
            return ""
        items.append({
          "file":p.name,"path":str(p),"pages":len(r.pages),
          "title":str(meta.get("/Title","") or ""),"author":str(meta.get("/Author","") or ""),
          "year_hits":sorted(set(re.findall(r"(?:19|20)\d{2}",clean[:8000])))[:8],
          "head":clean[:5000],
          "abstract":window([r"\babstract\b",r"摘\s*要"]),
          "conclusion":window([r"\bconclusions?\b",r"结\s*论",r"结\s*语",r"讨\s*论"]),
          "text_chars":len(full)
        })
    except Exception as e:
        items.append({"file":p.name,"path":str(p),"error":repr(e)})
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps([{"file":x["file"],"pages":x.get("pages"),"chars":x.get("text_chars"),"error":x.get("error")} for x in items],ensure_ascii=False,indent=2))
