from pathlib import Path
p=Path(r"F:\gugugaga\tmp\pdfs\build_academic_paper.py")
s=p.read_text(encoding='utf-8')
s=s.replace("assert len(r.pages)>=12","assert len(r.pages)>=10")
old="tex.append(r'\\section*{参考文献}\\begin{enumerate}')"
new=r'''tex.append(r'\appendix\section{36篇文献语料编码表}\begin{longtable}{p{12mm}p{63mm}p{31mm}p{45mm}}\toprule 编号 & 文献简称 & 主主题 & 主要贡献\\\midrule\endfirsthead\toprule 编号 & 文献简称 & 主主题 & 主要贡献\\\midrule\endhead')
for row in corpus_rows: tex.append(' & '.join(esc_tex(x) for x in row)+r'\\')
tex.append(r'\bottomrule\end{longtable}\section{系统级验证与验收矩阵}\begin{longtable}{p{26mm}p{50mm}p{75mm}}\toprule 试验 & 故障/工况注入 & 最低判据\\\midrule\endfirsthead\toprule 试验 & 故障/工况注入 & 最低判据\\\midrule\endhead')
for row in test_rows: tex.append(' & '.join(esc_tex(x) for x in row)+r'\\')
tex.append(r'\bottomrule\end{longtable}')
tex.append(r'\section*{参考文献}\begin{enumerate}')'''
if 'tex.append(r\'\\appendix' not in s and old in s:
    s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('finalized builder')
