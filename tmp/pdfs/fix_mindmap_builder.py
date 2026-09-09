from pathlib import Path
p=Path(r"F:\gugugaga\tmp\pdfs\build_city_ark_pdf.py")
s=p.read_text(encoding="utf-8")
s=s.replace('        mm = re.match(r"^(\\d+)\\.", heading)\n        if mm and mm.group(1) in MINDMAPS:\n            chapter = mm.group(1); center, branches = MINDMAPS[chapter]', '        chap_match = re.match(r"^(\\d+)\\.", heading)\n        if chap_match and chap_match.group(1) in MINDMAPS:\n            chapter = chap_match.group(1); center, branches = MINDMAPS[chapter]')
p.write_text(s,encoding="utf-8")
print("fixed")
