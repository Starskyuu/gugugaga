from pathlib import Path
p=Path(r"F:\gugugaga\tmp\pdfs\build_academic_paper.py")
s=p.read_text(encoding='utf-8')
insert=r'''

corpus_rows=[
('P01','扈海波（2016）城市暴雨积涝风险突增','洪涝风险/水文模型','场景与选址'),('P02','Pescaroli & Alexander（2016）级联灾害','关键基础设施','耦合失效'),('P03','Fekete（2020）洪水韧性与级联效应','关键基础设施','恢复与冗余'),('P04','Zhao等（2023）郑州7·20案例','极端暴雨治理','风险与治理'),('P05','谭徐明等（2009）洪涝应急响应','应急治理','指挥权责'),('P06','杨宇涵等（2023）ABM疏散','人群疏散','可达与容量'),('P07','Murphy等（2008）空水机器人实灾应用','灾害机器人','协同部署'),('P08','Yang等（2020）UAV-USV海上搜救','协同计算','任务/通信'),('P09','李海宏、吴吉东（2018）上海暴雨内涝','风险实证','监测阈值'),('P10','Jorge等（2019）灾害USV综述','灾害机器人','环境适应'),('P11','Queralta等（2020）多机器人搜救','多机器人','规划与感知'),('P12','Ozkan等 救援艇路径规划','洪水机器人','路网与航迹'),('P13','吕莹等（2025）空地联合搜救','空地协同','测绘-救援链'),('P14','刘祥等（2021）USV局部路径规划','无人艇算法','规划/避障'),('P15','Wang等（2020）Roboat II','城市水面平台','定位/坞泊'),('P16','Shen等（2023）USV融合定位','定位感知','GNSS退化'),('P17','余满江等（2025）USV集群强化学习','集群规划','算法泛化'),('P18','程顺才等（2022）受限通信任务分配','异构集群','断联协同'),('P19','Seba等（2019）灾时无线安全','网络安全','威胁与防护'),('P20','Miranda等（2016）灾后快速组网','应急通信','快速部署'),('P21','Kim等（2023）两栖桨轮机器人','两栖机构','复杂地表通过'),('P22','Luo等 自动停靠充电','自主补能','对准与接触'),('P23','Carreras-Coch等（2022）应急通信技术','通信综述','多制式权衡'),('P24','Gärtner等（2018）模块化空地车队','系统设计','模块与换电'),('P25','Sutoh等（2018）伸缩/折叠坡道','部署机构','收纳与可靠性'),('P26','Shetty等（2025）月球车坡道','部署机构','全流程验证'),('P27','López-Villegas等 UAV应急通信综述','无人机通信','架构与参数'),('P28','Jia等（2023）视觉-LiDAR停靠','自主补能','多传感对准'),('P29','Erdelj等（2017）WSN与多UAV','感知网络','阶段化架构'),('P30','高成等（2024）城市内涝预警','监测预警','物联与模型'),('P31','Wang等（2023）应急通信网络综述','应急通信','系统分类'),('P32','Wolf等（2022）多机构数字孪生','数字孪生','跨部门协同'),('P33','Lagap、Ghaffarian（2024）灾后孪生','数字孪生','风险恢复'),('P34','王伟等（2025）无人机基站部署','空中基站','位置-航迹联合'),('P35','张克寒等（2025）蓝绿灰协同','城市排涝','源-网-末端协同'),('P36','李燎原等（2026）无人机网络抗毁','拓扑韧性','动态连通')]

test_rows=[('黑启动','市电突失、冷机状态','核心负荷在目标时间内恢复；切换无危险'),('能源自持','连续低发电与峰值负荷','任务时长内能量平衡成立且保留安全余度'),('断网自治','公网、光纤和云同时断开','登记、调度、通信和控制维持最低功能'),('供水失效','市政水中断且原水受污染','分类水量达标；处理突破可被发现'),('污水失效','下水道倒灌/提升泵停机','厕所可用；污染物受控；无洁污交叉'),('满载环境','设计人口等效热湿负荷','温湿度、CO₂、颗粒物维持目标区间'),('机房失效','一个关键机房整体不可用','合理共因故障不致全部核心服务丧失'),('通信攻击','干扰、伪装、拒绝服务','攻击被隔离；数据最小化；纸质流程可接管'),('无人系统','GNSS拒止、丢包、动态障碍','安全返航/停机；可人工接管；日志完整'),('坞站污染','泥沙、雨淋、低照度、偏位','停靠补能成功率满足任务目标，无危险接触'),('人员减员','核心人员缺席50%','替补人员依据图卡完成安全启动和降级'),('补给中断','计划补给延迟一倍','库存策略触发；服务按优先级有序降级')]
'''
if 'corpus_rows=[' not in s:
    s=s.replace("def cite_pdf(s):",insert+"\ndef cite_pdf(s):")
s=s.replace("fontSize=9.3,leading=15.5","fontSize=10,leading=17.2")
s=s.replace("fontSize=8.8,leading=14","fontSize=9.2,leading=15")
append=r'''

story += [PageBreak(), Paragraph('附录A　36篇文献语料编码表',h1), Paragraph('本表列出全部本地PDF及其进入系统工程综合的主要主题。编码为多标签摘要，不替代原文的完整研究边界。',body)]
cdata=[[Paragraph(x,small) for x in ['编号','文献简称','主主题','对基站设计的主要贡献']]]+[[Paragraph(str(x),small) for x in r] for r in corpus_rows]
ct=Table(cdata,colWidths=[13*mm,67*mm,34*mm,44*mm],repeatRows=1,hAlign='LEFT')
ct.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0B7285')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#AAC5CA')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F6F7')]),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
story += [Paragraph('表A1　项目文献语料及其工程主题编码',caption),ct]
story += [PageBreak(),Paragraph('附录B　系统级验证与验收矩阵',h1),Paragraph('下列试验应在任务需求书冻结后转化为量化验收指标。所有阈值须结合服务人口、持续时间、所在地规范及运营能力确定。',body)]
tdata=[[Paragraph(x,small) for x in ['试验','故障/工况注入','最低判据']]]+[[Paragraph(str(x),small) for x in r] for r in test_rows]
tt=Table(tdata,colWidths=[29*mm,54*mm,75*mm],repeatRows=1,hAlign='LEFT')
tt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0B7285')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#AAC5CA')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F6F7')]),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
story += [Paragraph('表B1　城市方舟系统级故障注入与验收矩阵',caption),tt]
'''
needle="story += [CondPageBreak(60*mm),Paragraph('参考文献',h1)]"
if "附录A　36篇文献语料编码表" not in s:
    s=s.replace(needle,append+"\n"+needle)
s=s.replace("assert len(r.pages)>=12","assert len(r.pages)>=12")
p.write_text(s,encoding='utf-8')
print('expanded')
