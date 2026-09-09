from pathlib import Path
p=Path(r"F:\gugugaga\tmp\pdfs\build_academic_paper.py")
s=p.read_text(encoding='utf-8')
s=s.replace('"OZKAN M F, GARCIA CARRILLO L R, KING S A. Rescue boat path planning in flooded urban environments[C]. 2026."','"OZKAN M F, GARCIA CARRILLO L R, KING S A. Rescue boat path planning in flooded urban environments[C]//2019 IEEE International Symposium on Measurement and Control in Robotics. 2019. DOI:10.1109/ISMCR47492.2019.8955663."')
s=s.replace('"余满江, 何家伟, 邢博闻. 基于深度强化学习的无人艇集群路径规划[J]. 2025. DOI:10.11993/j.issn.2096-3920.2024-0179."','"余满江, 何家伟, 邢博闻. 基于深度强化学习的无人艇集群路径规划[J]. 水下无人系统学报, 2025, 33(2):380-388. DOI:10.11993/j.issn.2096-3920.2024-0179."')
s=s.replace('"程顺才, 杨萌, 宋锐. 通信受限情况下的无人水面艇集群复合任务分配算法[J]. 2022. DOI:10.3404/j.issn.1672-7649.2022.24.017."','"程顺才, 杨萌, 宋锐. 通信受限情况下的无人水面艇集群复合任务分配算法[J]. 舰船科学技术, 2022, 44(24):81-86. DOI:10.3404/j.issn.1672-7649.2022.24.017."')
s=s.replace("re.sub(r'^\\\\d+(?:\\\\.\\\\d+)?\\\\s*','',title)","re.sub(r'^\\d+(?:\\.\\d+)?\\s*','',title)")
p.write_text(s,encoding='utf-8')
print('references and LaTeX headings fixed')
