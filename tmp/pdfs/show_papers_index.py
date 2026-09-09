from pathlib import Path
import json, sys
items=json.loads(Path(r"F:\gugugaga\tmp\pdfs\papers_index.json").read_text(encoding="utf-8"))
start=int(sys.argv[1]); count=int(sys.argv[2])
for i,x in enumerate(items[start:start+count],start+1):
    print(f"\n===== [{i}] {x['file']} | pages={x.get('pages')} | title={x.get('title')} | author={x.get('author')} =====")
    print("HEAD:",x.get("head","")[:2200])
    print("ABSTRACT:",x.get("abstract","")[:2600])
    print("CONCLUSION:",x.get("conclusion","")[:2600])
