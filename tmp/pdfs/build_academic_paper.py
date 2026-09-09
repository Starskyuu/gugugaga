from pathlib import Path
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    PageBreak, Table, TableStyle, KeepTogether, Flowable, CondPageBreak)
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader

ROOT=Path(r"F:\gugugaga")
OUTDIR=ROOT/"10 现实难题"
PDF=OUTDIR/"城市方舟灾时应急救援基站现实建设技术难题_学术论文.pdf"
TEX=OUTDIR/"城市方舟灾时应急救援基站现实建设技术难题_学术论文.tex"

for name,path in [("YaHei",r"C:\Windows\Fonts\msyh.ttc"),("SimSun",r"C:\Windows\Fonts\simsun.ttc")]:
    if Path(path).exists(): pdfmetrics.registerFont(TTFont(name,path)); FONT=name; break
else: raise RuntimeError("未找到中文字体")

refs=[
"扈海波. 城市暴雨积涝灾害风险突增效应研究进展[J]. 地理科学进展, 2016, 35(9): 1075-1086. DOI:10.18306/dlkxjz.2016.09.003.",
"PESCAROLI G, ALEXANDER D. Critical infrastructure, panarchies and the vulnerability paths of cascading disasters[J]. Natural Hazards, 2016, 82: 175-192. DOI:10.1007/s11069-016-2186-3.",
"FEKETE A. Critical infrastructure and flood resilience: Cascading effects beyond water[J]. WIREs Water, 2020, 7: e1370. DOI:10.1002/wat2.1370.",
"ZHAO X, LI H, CAI Q, et al. Managing extreme rainfall and flooding events: A case study of the 20 July 2021 Zhengzhou flood in China[J]. Climate, 2023, 11: 228. DOI:10.3390/cli11110228.",
"谭徐明, 马建明, 张念强. 洪涝灾害应急响应调查及其若干问题探讨[J]. 中国水利水电科学研究院学报, 2009, 7(3): 216-221.",
"杨宇涵, 殷杰, 王丹丹, 等. 基于ABM的城市暴雨洪涝灾害应急疏散仿真研究——以河南郑州‘7·20’特大暴雨洪涝灾害为例[J]. 中国科学:地球科学, 2023, 53(2):267-276. DOI:10.1360/SSTe-2022-0094.",
"MURPHY R R, STEIMLE E, GRIFFIN C, et al. Cooperative use of unmanned sea surface and micro aerial vehicles at Hurricane Wilma[J]. Journal of Field Robotics, 2008. DOI:10.1002/rob.20235.",
"YANG T, JIANG Z, SUN R, et al. Maritime search and rescue based on group mobile computing for unmanned aerial vehicles and unmanned surface vehicles[J]. IEEE Transactions on Industrial Informatics, 2020, 16(12):7700-7710. DOI:10.1109/TII.2020.2974047.",
"李海宏, 吴吉东. 2007—2016年上海市暴雨特征及其与内涝灾情关系分析[J]. 自然资源学报, 2018, 33(12):2136-2148. DOI:10.31497/zrzyxb.20180559.",
"JORGE V A M, GRANADA R, MAIDANA R G, et al. A survey on unmanned surface vehicles for disaster robotics: Main challenges and directions[J]. Sensors, 2019, 19(3):702. DOI:10.3390/s19030702.",
"PEÑA QUERALTA J, TAIPALMAA J, PULLINEN B C, et al. Collaborative multi-robot search and rescue: Planning, coordination, perception, and active vision[J]. IEEE Access, 2020. DOI:10.1109/ACCESS.2020.3030190.",
"OZKAN M F, GARCIA CARRILLO L R, KING S A. Rescue boat path planning in flooded urban environments[C]//2019 IEEE International Symposium on Measurement and Control in Robotics. 2019. DOI:10.1109/ISMCR47492.2019.8955663.",
"吕莹, 李悦, 孙会君. 洪涝灾害场景下空地联合的搜救路径规划[J]. 系统管理学报, 2025, 34(5):1305-1315. DOI:10.3969/j.issn.2097-4558.2025.05.009.",
"刘祥, 叶晓明, 王泉斌, 等. 无人水面艇局部路径规划算法研究综述[J]. 中国舰船研究, 2021, 16(增刊1):1-10. DOI:10.19693/j.issn.1673-3185.02538.",
"WANG W, SHAN T, LEONI P, et al. Roboat II: A novel autonomous surface vessel for urban environments[C]. IEEE/RSJ International Conference on Intelligent Robots and Systems, 2020.",
"SHEN W, YANG Z, YANG C, et al. A LiDAR SLAM-assisted fusion positioning method for USVs[J]. Sensors, 2023, 23:1558. DOI:10.3390/s23031558.",
"余满江, 何家伟, 邢博闻. 基于深度强化学习的无人艇集群路径规划[J]. 水下无人系统学报, 2025, 33(2):380-388. DOI:10.11993/j.issn.2096-3920.2024-0179.",
"程顺才, 杨萌, 宋锐. 通信受限情况下的无人水面艇集群复合任务分配算法[J]. 舰船科学技术, 2022, 44(24):81-86. DOI:10.3404/j.issn.1672-7649.2022.24.017.",
"SEBA A, NOUALI-TABOUDJEMAT N, BADACHE N, et al. A review on security challenges of wireless communications in disaster emergency response and crisis management situations[J]. Journal of Network and Computer Applications, 2019, 126:150-161. DOI:10.1016/j.jnca.2018.11.010.",
"MIRANDA K, MOLINARO A, RAZAFINDRALAMBO T. A survey on rapidly deployable solutions for post-disaster networks[J]. IEEE Communications Magazine, 2016. DOI:10.1109/MCOM.2016.7452275.",
"KIM C, LEE K, RYU S, et al. Amphibious robot with self-rotating paddle-wheel mechanism[J]. IEEE/ASME Transactions on Mechatronics, 2023, 28(4):1836-1848. DOI:10.1109/TMECH.2023.3273240.",
"CARRERAS-COCH A, NAVARRO J, SANS C, et al. Communication technologies in emergency situations[J]. Electronics, 2022, 11:1155. DOI:10.3390/electronics11071155.",
"GÄRTNER A C, FERRIERO D, BAYRAK A E, et al. Integrated system design of a modular, autonomous, aerial and ground vehicle fleet for disaster relief missions: A case study[C]. DESIGN 2018. DOI:10.21278/idc.2018.0477.",
"SUTOH M, HOSHINO T, WAKABAYASHI S. Rover deployment system for lunar landing mission[J]. Acta Astronautica, 2018. DOI:10.1016/j.actaastro.2017.06.019.",
"JIA F, AFAQ M, RIPKA B, et al. Vision- and LiDAR-based autonomous docking and recharging of a mobile robot[J]. Applied Sciences, 2023, 13:10675. DOI:10.3390/app131910675.",
"ERDELJ M, KRÓL M, NATALIZIO E. Wireless sensor networks and multi-UAV systems for natural disaster management[J]. Computer Networks, 2017, 124:72-86. DOI:10.1016/j.comnet.2017.05.021.",
"高成, 佘亮亮, 顾春旭, 等. 城市内涝预警预报系统研发及应用[J]. 中国水利, 2024(3):34-39.",
"WANG Q, LI W, YU Z, et al. An overview of emergency communication networks[J]. Remote Sensing, 2023, 15:1595. DOI:10.3390/rs15061595.",
"WOLF K, DAWSON R J, MILLS J P, et al. Towards a digital twin for supporting multi-agency incident management in a smart city[J]. Scientific Reports, 2022, 12:16221. DOI:10.1038/s41598-022-20178-8.",
"LAGAP U, GHAFFARIAN S. Digital post-disaster risk management twinning: A review and improved conceptual framework[J]. International Journal of Disaster Risk Reduction, 2024, 110:104629. DOI:10.1016/j.ijdrr.2024.104629.",
"王伟, 陈志刚, 何春蛟, 等. 灾害应急通信场景下无人机基站位置部署与路径规划[J]. 交通运输工程与信息学报, 2025, 23(4):22-35.",
"张克寒, 梅超, 刘家宏, 等. 蓝绿灰基础设施协同的城市内涝调控及关键技术解析[J]. 水利水电技术(中英文), 2025, 56(6):26-37. DOI:10.13928/j.cnki.wrahe.2025.06.003.",
"李燎原, 骆西建, 权冀川, 等. 面向辅助通信的无人机基站网络拓扑抗毁研究综述[J]. 计算机技术与发展, 2026, 36(6):1-11. DOI:10.20165/j.cnki.ISSN1673-629X.2026.0024."
]

sections=[
("1 引言",[
"极端降雨、快速城市化和高密度基础设施网络共同改变了城市灾害的风险形态。城市不透水面扩张、排水能力不足和人口资产集中会放大积涝暴露，高时空分辨率降雨与排水数据因此成为风险识别的基础{cite:1,9}。郑州‘7·20’事件进一步表明，预警、交通、地下空间、通信和组织响应的缺口会在短时极端降雨中叠加{cite:4,6}。",
"与此同时，电力、通信、供水、交通等关键基础设施并非彼此独立。级联灾害研究指出，功能网络的相互依赖会把局部故障放大为跨部门、跨尺度的服务中断；灾害后果不仅来自自然触发因素，也来自脆弱性、反馈回路和资源调度方式{cite:2,3}。因此，以单栋建筑或单一装备为对象的设计方法不足以支撑灾时连续运行。",
"本文将‘城市方舟’界定为一种平灾两用、可快速转换、具备有限离网能力，并可部署空中—水面—地面无人系统的社区级应急救援基站。研究目的不是给出未经场地约束的设备清单，而是回答三个问题：第一，现实建设必须关闭哪些技术风险；第二，这些风险如何相互耦合；第三，概念模型应通过何种分阶段验证转化为可审批、可运维的工程实体。"
]),
("2 研究材料与方法",[
"研究采用语料库范围综述与系统工程综合相结合的方法。资料范围为项目目录‘01 papers’中的全部36篇PDF，共538页；按主要文字构成计，中文17篇、英文19篇。语料时间大体覆盖2008—2026年，主题包括城市洪涝风险、关键基础设施级联、疏散仿真、应急通信、无人机/无人艇协同、定位与路径规划、自动停靠补能以及数字孪生。该语料由项目预先提供，并非经多个数据库检索得到，故本文不将其表述为完整的系统综述。",
"编码分三步进行。首先提取题名、作者、年份、摘要、结论、DOI及关键工程论断；其次按‘危险源—功能—设备—接口—失效模式—验证方法’进行多标签编码；最后采用功能分解、故障模式与影响分析思路，将文献结论翻译为基站级设计要求。每个技术难题均区分A类直接证据与B类系统工程推论：A类指语料中存在案例、实验、模型或综述支持；B类指基站保持完整服务链所必需，但现有语料缺少足够专项证据。",
"分析边界以暴雨洪涝为主要触发场景，同时保留地震、火灾、极端温度、危化品和公共卫生事件的接口要求。本文不进行具体地块的结构计算、容量定额或设备选型；所有数值参数均需在场地、服务人口、自持时间和适用规范确定后校准。"
]),
("3 系统定义与性能边界",[
"城市方舟应被视为社会—技术系统，而非简单的避难建筑。其最低功能包括：灾情感知与信息汇聚、应急通信、人员分流与初步医疗、临时安置、饮水与卫生、关键负荷供电、物资周转、无人装备收发与维护以及社区指挥。谭徐明等强调，应急启动、响应和跨部门权责必须清晰区分{cite:5}；数字孪生研究也表明，多机构事件管理的价值取决于数据互操作、实时性和共同态势图，而非单纯平台建设{cite:29,30}。",
"有效容量不能由建筑面积单独确定。设空间、饮水、卫生、通风、供电、医疗、人员、疏散与补给分别支持的人数为N_s、N_w、N_h、N_v、N_e、N_m、N_p、N_x和N_l，则基站在给定自持时长T下的有效容量为：{equation:N_eff(T)=min(N_s,N_w,N_h,N_v,N_e,N_m,N_p,N_x,N_l)}。该木桶约束要求所有专业使用同一任务剖面与人口假设。",
"性能边界至少应包含正常、应急、最低生存与安全停用四种状态，并为每项功能规定启动时间、允许中断时间、最低输出和恢复时间。冗余设计还必须避免共因失效，例如两套电源位于同一淹水机房、两条通信链路共用同一回传或所有无人平台依赖单一定位源。"
]),
("4 现实建设中的关键技术难题",[]),
("4.1 多灾种建模、选址与洪涝边界",[
"暴雨危险性应同时描述雨强、历时和空间分布，而地表敏感性取决于土地覆盖、地形、管网及其动态状态{cite:1,9}。蓝—绿—灰基础设施协同研究表明，源头减排、调蓄与末端排放的效能随降雨情景变化，不能把某类设施作为超标暴雨下的单一屏障{cite:32}。因此基站选址需叠加积水深度、流速、到达时间、污染源、断路概率、人员暴露及周边建筑次生风险。",
"难点在于风险的非平稳性和灾后路网变化。洪水会降低疏散速度并改变可达路径，ABM研究显示大范围积涝可使灾后疏散效率显著下降，避难场所布局和容量也会改变整体效果{cite:6}。工程上应以动态洪涝图而非静态行政距离划定服务半径，并设置两条以上物理独立的到达与补给路线。"
]),
("4.2 结构、围护与展开机构的灾后可使用性",[
"结构设计目标不能停留在‘不倒塌’，还应控制残余变形、非结构构件脱落、设备锚固和机电接口破坏，使建筑在灾后可被快速判定为可用。对洪涝场景而言，关键机房标高、可淹没层、挡水接口和漂浮物冲击同样决定功能连续性。上述内容在现有语料中属于B类证据空白，需补充建筑抗震、抗风、防洪及非结构构件专项研究。",
"若基站包含可展开舱体、坡道或机器人坞站，机构必须兼顾收纳体积、载荷、地面高差、泥沙污染和失电手动操作。折叠/伸缩坡道及灾害机器人模块化研究提示，部署可靠性取决于机构刚度、容差、锁止、感知和原型验证，而不仅是几何可展开{cite:23,24}。月面坡道技术不能直接移植到城市救灾，但其需求分解与全流程验证方法具有借鉴价值。"
]),
("4.3 离网能源、黑启动与自主补能",[
"无人机、无人艇、通信、净水、通风、照明、医疗和冷链构成多时间尺度负荷。系统首先应划分不可中断、生命安全、重要与可延迟负荷，再进行功率、能量、启动冲击、温度降额和老化联合校核。太阳能与储能只能在给定气候和任务剖面下评价；发电机又引入燃料补给、尾气、噪声与消防风险。现有语料缺少微电网与建筑储能专项证据，因此容量结论必须作为后续实验和规范校核项。",
"持续自主作业还要求自动停靠、充电或换电。机器视觉与LiDAR辅助停靠研究表明，末端对准、遮挡、照度、定位误差和接触可靠性是关键{cite:25}；模块化无人系统研究说明自动更换电池可延长任务范围，但同时引入机械、控制与接口复杂性{cite:23}。基站应保留人工拖带、旁路供电和通用充电接口，避免自动坞站成为单点故障。"
]),
("4.4 水、卫生、环境控制与医疗连续性",[
"真实收容能力往往先受饮水、厕所、污水、通风或工作人员限制。供水应区分饮用、医疗、洗手、清洁、烹饪和消防用途；处理链需根据微生物、浑浊度、化学污染和盐分选择多重屏障，并考虑无电重力供水、储水轮换与耗材库存。市政污水失效时还需预设密闭储存、干式卫生或转运接口。",
"密集收容会提高热湿负荷、二氧化碳和感染传播风险；室外烟气或化学污染又可能迫使新风系统切换为防护模式。医疗空间则需明确分诊等级、冷链、氧气、隔离、慢病药物和转运边界。由于现有36篇语料几乎没有水卫、暖通、医疗与感染控制专项研究，这一组属于最重要的B类证据缺口：不能因文献库缺少而从设计中删除，反而应优先补充规范、医院工程和人道救援标准。"
]),
("4.5 应急通信、边缘计算与网络安全",[
"灾时通信面临基站损毁、回传中断、拥塞、能源不足和用户空间分布突变。快速部署网络可由便携基站、车载节点、无人机中继、卫星、D2D、Mesh和机会网络组合，但不同方案在覆盖、容量、时延、能耗、频谱许可和部署时间上存在权衡{cite:20,22,28}。无人机基站位置与航迹必须联合优化，单独追求覆盖面积可能导致续航或回传不可行{cite:31,33}。",
"多制式并不自动等于韧性。系统必须检查不同链路是否共用电源、天线位置、核心网或云服务，并建立离线身份登记、任务调度和数据冲突合并机制。安全综述指出，应急无线网络同样面临窃听、伪装、拒绝服务、节点俘获和路由攻击，而灾时的临时组网与弱认证会进一步放大风险{cite:19}。故基站应实行最小数据采集、分区授权、端到端加密、离线审计和纸质兜底。"
]),
("4.6 感知、预警与数字孪生的可信性",[
"内涝预警系统可融合物联感知、降雨监测、水动力模型、大数据分析和在线风险图{cite:27}。数字孪生可支持多部门共享交通、天气、摄像和传感数据，并用于路线重规划和态势推演{cite:29,30}。但平台价值受制于数据时效、模型偏差、传感器漂移、接口语义和灾时算力/网络可用性。",
"基站数字孪生不应成为必须联网才能运行的上层控制器。建议采用‘本地自治—边缘汇聚—云端协同’三级架构：底层能源、水、门禁和通风控制器在断网上仍能安全运行；边缘节点维持局部态势和数据缓存；云端仅承担跨站优化与长期分析。关键决策应显示数据来源、更新时间、置信区间与替代流程。"
]),
("4.7 空—水—地无人系统的协同部署",[
"无人机适合快速测绘、通信中继和目标发现；无人艇/两栖机器人适合被淹道路中的物资和人员接近；地面平台可承担搬运和近距巡检。实灾部署表明，空中与水面平台能形成互补感知，但水流、杂物、通信、发射回收和操作员负担会限制效果{cite:7,10}。WSN与多无人机综述也强调，灾害阶段、网络覆盖和任务目标必须共同决定系统架构{cite:26}。",
"协同难点包括：GNSS遮挡与多路径、LiDAR/视觉退化、动态障碍、航道宽度和水深不确定、异构任务分配、通信受限下的一致性以及人机接管。多传感融合定位、局部路径规划、空地联合规划和受限通信任务分配分别提供了局部解法{cite:13,14,16,18}，但尚不能替代整站级验证。深度强化学习在仿真中可改善收敛与路径质量{cite:17}，其域外泛化、可解释性和安全边界仍需实地测试。"
]),
("4.8 人群疏散、无障碍与空间组织",[
"疏散不是最短路径问题。个体风险感知、决策者比例、响应延迟、家庭同行、拥堵和积水深度会共同改变结果{cite:6}。站内还存在登记、安检、分诊、物资领取、厕所和咨询多个队列，任一瓶颈均可能阻塞消防与医疗通道。",
"空间设计应采用洁净、半污染、污染分区和人流—物流—废物流分离，设置轮椅、担架、儿童、老人、视听障碍者及非本地语言人群的完整服务链。服务半径与收容量必须在灾后路网模型中复核，并通过角色扮演和实人演练校准，而不能仅依靠规范疏散时间。"
]),
("4.9 物流、治理、平灾转换与全寿命运维",[
"应急库存会过期、失窃并占用空间；燃料、滤芯、电池、药品和防护用品的保质期及补给周期不同。物资策略应基于消耗率、补给延迟和替代品可得性，采用多点储备、批次追踪、平时轮换和断网盘点。机器人与通信设备还需备件、固件、频谱许可和受训操作员。",
"治理失败会使技术系统失效。应明确产权人、运营人、启动授权、应急指挥、维护责任和年度预算，并把平时用途与灾时清场权写入制度。现有研究指出，应急响应需在统一指挥下区分启动主体和行动主体{cite:5}；关键基础设施韧性也依赖资源调度、社会反馈和组织学习{cite:2,3}。因此，平灾转换时间、人员减员场景和供应商退出均应进入验收。"
]),
("5 耦合失效模型与总体架构",[
"基站的核心风险来自跨系统耦合。设功能节点集合V包含电力、水务、通信、通风、医疗、物流与人员，依赖关系E构成有向图G=(V,E)。节点i在时刻t的服务水平记为S_i(t)∈[0,1]，当上游j低于阈值θ_ji时，i的能力按耦合系数w_ji衰减。设计目标不是保证所有节点始终满额，而是使关键功能集合K满足{equation:for all i in K, integral_0^T S_i(t)dt >= A_i,min}，并在故障后规定时间内恢复。",
"典型链路为：市电失效→泵站、通信、通风和冷链降级→卫生与医疗压力上升→人员冲突和运维错误增加。另一链路为：积水淹没道路→补给与转运中断→燃料、药品和废物储存接近上限→有效容量下降。级联灾害理论要求设计者寻找升级点和社会节点{cite:2}，而非只计算设备独立可靠度。",
"总体架构建议采用四层：第一层为安全场地和灾后可用建筑；第二层为电、水、卫生、通风、消防等离网生命线；第三层为通信、边缘计算、感知和无人装备；第四层为人员、流程、治理与外部协同。各层应支持局部自治、手动旁路和可观测状态，并通过接口控制文件约束机械、电气、数据和责任边界。"
]),
("6 分阶段工程化路线",[
"阶段A为任务与场景冻结：明确目标城市、服务人口、灾种组合、自持时间、最低服务水平、候选地块和运营主体。阶段B为数字样机与台架：建立统一水量—能量—物资—人员模型，完成能源、净水、通信、坞站和控制器独立试验。阶段C为1:1功能舱：在夜间、雨淋、泥沙、低照度和断网条件下，由真实运营人员完成部署。",
"阶段D为整站试点：开展满载或等效带载、断电黑启动、断网自治、市政供水/污水失效、关键人员缺席和单机房不可用试验。阶段E为网络化复制：形成不同等级站型、跨站库存和无人平台调度。每阶段设置证据门槛；若服务人口、有效容量、运营经费或共因失效尚未关闭，不应以施工进度替代风险关闭。"
]),
("7 验证、验收与可证伪指标",[
"验收应从‘设备是否安装’转向‘任务是否完成’。系统级试验至少包括：市电突然中断后的孤岛与黑启动；公网、光纤和云平台同时不可用；市政供水和污水完全中断；设计人口等效热湿与物耗负荷；单个关键机房失效；补给延迟一倍；核心人员减少50%；以及网络攻击和错误传感器注入。",
"建议建立六类通过标准：安全性——不产生不可接受的火灾、触电、污染和疏散风险；功能性——关键服务按时启动并维持；容量一致性——所有子系统同时支持声明人口；韧性——合理单点故障不导致全部核心功能丧失；可操作性——普通受训人员可依据现场图卡操作；可恢复性——故障可定位、隔离、旁路并在目标时间内修复。",
"无人系统应单独验证发射回收成功率、通信丢包下任务完成、GNSS拒止定位、动态障碍避让、低电量返航、人员接管和坞站污染容差。仿真中的算法优势不能直接作为安全证明；实地试验应覆盖未见场景并保留完整日志。"
]),
("8 讨论：证据充分性与研究缺口",[
"本语料对洪涝机理、疏散、应急通信、无人系统和数字孪生提供了较强支持。例如，联合位置—航迹优化、异构平台协同、多传感定位和受限通信任务分配均有明确方法证据{cite:8,11,13,16,31}。这些研究说明基站可作为感知、通信、计算、补能和任务调度的综合母站，而不只是仓储点。",
"但文献结构也造成明显偏差。第一，缺少建筑结构、非结构构件、防洪围护和消防工程研究；第二，缺少离网微电网、储能消防和燃料轮换证据；第三，水处理、厕所、污水、暖通、感染控制和医疗连续性几乎未覆盖；第四，长期运维、全寿命成本、社区接受度、隐私和责任制度证据不足。因此，本文对这些领域给出的是完整系统所必需的研究议程，而非由当前语料证明的定型方案。",
"此外，多数机器人与通信研究以仿真、受控实验或海事环境为主，城市洪涝中的浑水、漂浮物、窄巷、电磁遮挡、人员密集和长期值守会降低外部有效性。后续研究应以真实地块和运营主体为对象，将算法指标转换为任务完成率、连续服务时长、人工干预次数和故障恢复时间。"
]),
("9 结论",[
"现实建设城市方舟的首要任务，是把概念模型转换为可量化任务需求，并以有效容量而非建筑面积声明能力。技术难题可归纳为九个相互依赖的领域：多灾种选址、灾后可用结构、离网能源、水卫与环境控制、韧性通信、可信数字孪生、空水地无人协同、人群疏散以及治理运维。",
"其中，洪涝风险、通信与无人系统已有较丰富的直接证据；结构、电力、水卫、医疗和消防仍是必须优先补齐的证据缺口。项目应采用‘需求冻结—数字样机—台架—1:1功能舱—整站试点—网络复制’的门控路线，并通过断电、断网、断水、满载、减员和共因故障试验证明能力。城市方舟是否成立，最终不取决于设备数量，而取决于灾害中目标人群能否到达、核心服务能否持续、故障能否安全降级，以及这种能力能否在全寿命周期内被维护和审计。"
])]

challenge_rows=[
('灾害与选址','降雨/积水非平稳；灾后路网变化','A','高分辨率水文-路网联合模型；双路径可达','1,4,6,9,32'),
('结构与围护','生命安全不等于灾后可用','B','性能化结构、设备锚固、防洪标高、快速检查','—'),
('展开机构','泥沙、高差、锁止与手动回收','A/B','全尺度原型；失电和污染容差试验','23,24'),
('能源微网','功率/能量/黑启动/燃料共同约束','B','负荷分级、多源供能、72 h带载、手动旁路','—'),
('自动补能','末端对准与接触可靠性','A','视觉-LiDAR融合、人工拖带、通用接口','23,25'),
('供水净水','水源污染与储水卫生','B','分类水量、多屏障处理、无电供水','—'),
('厕所污水','市政接口中断后快速限容','B','干式/密闭方案、物料平衡、清运接口','—'),
('热环境医疗','满员热湿、烟气、感染与冷链','B','最小通风独立供电、分区、医疗能力分级','—'),
('应急通信','覆盖、容量、回传、能耗与频谱权衡','A','多制式、离线优先、边缘自治','19,20,22,28,31'),
('网络安全','临时组网弱认证与节点暴露','A','最小数据、加密、审计、纸质兜底','19'),
('感知孪生','数据失真、接口异构、云依赖','A','显示置信度；本地自治-边缘-云三级架构','27,29,30'),
('无人协同','异构感知、定位、规划与任务分配','A','任务分层、受限通信策略、人机接管','7,8,10-18,26'),
('人群无障碍','行为与积水共同改变疏散效率','A/B','ABM+实人演练；全链路无障碍','6'),
('物流库存','补给不确定、过期与备件锁定','B','消耗模型、多点库存、替代品目录','—'),
('治理转换','启动权、指挥权、清场与责任模糊','A','RACI、平灾转换演练、统一指挥','2,3,5'),
('全寿命运维','闲置失修、供应商退出、能力不可证','B','年度带载、校准、轮换、第三方审计','—')]



corpus_rows=[
('P01','扈海波（2016）城市暴雨积涝风险突增','洪涝风险/水文模型','场景与选址'),('P02','Pescaroli & Alexander（2016）级联灾害','关键基础设施','耦合失效'),('P03','Fekete（2020）洪水韧性与级联效应','关键基础设施','恢复与冗余'),('P04','Zhao等（2023）郑州7·20案例','极端暴雨治理','风险与治理'),('P05','谭徐明等（2009）洪涝应急响应','应急治理','指挥权责'),('P06','杨宇涵等（2023）ABM疏散','人群疏散','可达与容量'),('P07','Murphy等（2008）空水机器人实灾应用','灾害机器人','协同部署'),('P08','Yang等（2020）UAV-USV海上搜救','协同计算','任务/通信'),('P09','李海宏、吴吉东（2018）上海暴雨内涝','风险实证','监测阈值'),('P10','Jorge等（2019）灾害USV综述','灾害机器人','环境适应'),('P11','Queralta等（2020）多机器人搜救','多机器人','规划与感知'),('P12','Ozkan等 救援艇路径规划','洪水机器人','路网与航迹'),('P13','吕莹等（2025）空地联合搜救','空地协同','测绘-救援链'),('P14','刘祥等（2021）USV局部路径规划','无人艇算法','规划/避障'),('P15','Wang等（2020）Roboat II','城市水面平台','定位/坞泊'),('P16','Shen等（2023）USV融合定位','定位感知','GNSS退化'),('P17','余满江等（2025）USV集群强化学习','集群规划','算法泛化'),('P18','程顺才等（2022）受限通信任务分配','异构集群','断联协同'),('P19','Seba等（2019）灾时无线安全','网络安全','威胁与防护'),('P20','Miranda等（2016）灾后快速组网','应急通信','快速部署'),('P21','Kim等（2023）两栖桨轮机器人','两栖机构','复杂地表通过'),('P22','Luo等 自动停靠充电','自主补能','对准与接触'),('P23','Carreras-Coch等（2022）应急通信技术','通信综述','多制式权衡'),('P24','Gärtner等（2018）模块化空地车队','系统设计','模块与换电'),('P25','Sutoh等（2018）伸缩/折叠坡道','部署机构','收纳与可靠性'),('P26','Shetty等（2025）月球车坡道','部署机构','全流程验证'),('P27','López-Villegas等 UAV应急通信综述','无人机通信','架构与参数'),('P28','Jia等（2023）视觉-LiDAR停靠','自主补能','多传感对准'),('P29','Erdelj等（2017）WSN与多UAV','感知网络','阶段化架构'),('P30','高成等（2024）城市内涝预警','监测预警','物联与模型'),('P31','Wang等（2023）应急通信网络综述','应急通信','系统分类'),('P32','Wolf等（2022）多机构数字孪生','数字孪生','跨部门协同'),('P33','Lagap、Ghaffarian（2024）灾后孪生','数字孪生','风险恢复'),('P34','王伟等（2025）无人机基站部署','空中基站','位置-航迹联合'),('P35','张克寒等（2025）蓝绿灰协同','城市排涝','源-网-末端协同'),('P36','李燎原等（2026）无人机网络抗毁','拓扑韧性','动态连通')]

test_rows=[('黑启动','市电突失、冷机状态','核心负荷在目标时间内恢复；切换无危险'),('能源自持','连续低发电与峰值负荷','任务时长内能量平衡成立且保留安全余度'),('断网自治','公网、光纤和云同时断开','登记、调度、通信和控制维持最低功能'),('供水失效','市政水中断且原水受污染','分类水量达标；处理突破可被发现'),('污水失效','下水道倒灌/提升泵停机','厕所可用；污染物受控；无洁污交叉'),('满载环境','设计人口等效热湿负荷','温湿度、CO₂、颗粒物维持目标区间'),('机房失效','一个关键机房整体不可用','合理共因故障不致全部核心服务丧失'),('通信攻击','干扰、伪装、拒绝服务','攻击被隔离；数据最小化；纸质流程可接管'),('无人系统','GNSS拒止、丢包、动态障碍','安全返航/停机；可人工接管；日志完整'),('坞站污染','泥沙、雨淋、低照度、偏位','停靠补能成功率满足任务目标，无危险接触'),('人员减员','核心人员缺席50%','替补人员依据图卡完成安全启动和降级'),('补给中断','计划补给延迟一倍','库存策略触发；服务按优先级有序降级')]

def cite_pdf(s):
    return re.sub(r'\{cite:([^}]+)\}',lambda m:f'<super>[{m.group(1)}]</super>',s)
def cite_tex(s):
    return re.sub(r'\{cite:([^}]+)\}',lambda m:r'\textsuperscript{['+m.group(1)+']}',s)
def esc_tex(s):
    for a,b in [('\\','\\textbackslash{}'),('&','\\&'),('%','\\%'),('#','\\#'),('_','\\_')]: s=s.replace(a,b)
    return s

# ---------- LaTeX source ----------
tex=[r'''\documentclass[UTF8,a4paper,zihao=-4]{ctexart}
\usepackage{geometry,booktabs,longtable,array,amsmath,graphicx,hyperref,fancyhdr,xcolor}
\geometry{left=25mm,right=25mm,top=24mm,bottom=24mm}
\hypersetup{colorlinks=true,linkcolor=black,citecolor=black,urlcolor=blue}
\pagestyle{fancy}\fancyhf{}\lhead{城市方舟灾时应急救援基站现实建设技术难题}\rhead{\thepage}
\title{从微缩概念到现实基站：\\“城市方舟”灾时应急救援基站建设的关键技术难题\\——基于36篇文献的范围综述与系统工程综合}
\author{城市方舟项目组}\date{2026年9月}
\begin{document}\maketitle
\begin{abstract}
面向城市极端灾害中电力、供水、通信、交通和治理同步失效的情景，本文讨论“城市方舟”灾时应急救援基站从微缩概念模型走向现实建设所必须解决的技术难题。研究对项目提供的36篇PDF文献（共538页）开展语料库范围综述，并以“危险源—功能—设备—接口—失效模式—验证方法”为编码链条进行系统工程综合。结果表明，基站有效性由多灾种选址、灾后可使用结构、离网能源、水与卫生、热环境与医疗、应急通信、感知与数字孪生、空—水—地无人系统、人群疏散、物流治理和全寿命运维共同决定。文献对洪涝风险、基础设施级联、通信和无人系统提供了直接证据，但对结构、微电网、水卫、暖通、医疗和消防的专项证据明显不足。本文提出有效容量木桶模型、四层系统架构、分阶段工程化路线及可证伪的验收试验。研究认为，城市方舟应被建设为可局部自治、可手动旁路、可安全降级且可持续审计的社会—技术系统，而非设备堆叠式避难设施。
\end{abstract}
\noindent\textbf{关键词：}城市方舟；应急救援基站；城市洪涝；关键基础设施；应急通信；无人系统；灾害韧性

\begin{abstract}
\textbf{Abstract:} This paper identifies the engineering barriers that must be resolved before the “Urban Ark” can evolve from a miniature concept into a deployable urban emergency-response base. A corpus-based scoping review of 36 project-supplied PDF papers (538 pages) is combined with systems-engineering synthesis. The results show that real-world viability depends on coupled performance across multi-hazard siting, post-event structural usability, islanded energy, water and sanitation, environmental and medical continuity, resilient communications, trustworthy sensing and digital twins, heterogeneous unmanned systems, evacuation, logistics, governance, and life-cycle maintenance. Strong direct evidence exists for flood risk, cascading infrastructure failure, emergency communications and robotics, while major evidence gaps remain in structural engineering, microgrids, WASH, HVAC, medical continuity and fire safety. A bottleneck capacity model, four-layer architecture, gated development pathway and falsifiable acceptance tests are proposed.
\end{abstract}
\noindent\textbf{Keywords:} Urban Ark; emergency response base; urban flooding; critical infrastructure; emergency communications; unmanned systems; resilience
''']
for title,paras in sections:
    level=2 if re.match(r'^\d+\.\d+',title) else 1
    cmd='subsection' if level==2 else 'section'
    tex.append(f"\\{cmd}{{{esc_tex(re.sub(r'^\d+(?:\.\d+)?\s*','',title))}}}")
    for p in paras:
        if p.startswith('{equation:'):
            tex.append('\\begin{equation}'+p[10:-1]+'\\end{equation}')
        elif '{equation:' in p:
            before,eq=p.split('{equation:',1); eq=eq[:-1]
            tex.append(cite_tex(esc_tex(before))+'\\begin{equation}'+eq+'\\end{equation}')
        else: tex.append(cite_tex(esc_tex(p)))
    if title.startswith('4 现实'):
        tex.append(r'''\begin{longtable}{p{20mm}p{37mm}p{9mm}p{50mm}p{22mm}}
\caption{城市方舟建设技术难题、证据等级与验证方向}\\\toprule
难题 & 核心失效 & 证据 & 工程响应 & 语料来源\\\midrule\endfirsthead
\toprule 难题 & 核心失效 & 证据 & 工程响应 & 语料来源\\\midrule\endhead''')
        for r in challenge_rows: tex.append(' & '.join(esc_tex(x) for x in r)+r'\\')
        tex.append(r'\bottomrule\end{longtable}')
tex.append(r'\appendix\section{36篇文献语料编码表}\begin{longtable}{p{12mm}p{63mm}p{31mm}p{45mm}}\toprule 编号 & 文献简称 & 主主题 & 主要贡献\\\midrule\endfirsthead\toprule 编号 & 文献简称 & 主主题 & 主要贡献\\\midrule\endhead')
for row in corpus_rows: tex.append(' & '.join(esc_tex(x) for x in row)+r'\\')
tex.append(r'\bottomrule\end{longtable}\section{系统级验证与验收矩阵}\begin{longtable}{p{26mm}p{50mm}p{75mm}}\toprule 试验 & 故障/工况注入 & 最低判据\\\midrule\endfirsthead\toprule 试验 & 故障/工况注入 & 最低判据\\\midrule\endhead')
for row in test_rows: tex.append(' & '.join(esc_tex(x) for x in row)+r'\\')
tex.append(r'\bottomrule\end{longtable}')
tex.append(r'\section*{参考文献}\begin{enumerate}')
for r in refs: tex.append(r'\item '+esc_tex(r))
tex.append(r'\end{enumerate}\end{document}')
OUTDIR.mkdir(parents=True,exist_ok=True); TEX.write_text('\n\n'.join(tex),encoding='utf-8')

# ---------- PDF layout ----------
PAGE_W,PAGE_H=A4; ML=22*mm; MR=20*mm; MT=20*mm; MB=19*mm
body=ParagraphStyle('body',fontName=FONT,fontSize=10,leading=17.2,alignment=TA_JUSTIFY,textColor=colors.HexColor('#1E2B32'),spaceAfter=6,firstLineIndent=18)
h1=ParagraphStyle('h1',fontName=FONT,fontSize=15,leading=21,textColor=colors.HexColor('#123B52'),spaceBefore=13,spaceAfter=7,keepWithNext=True)
h2=ParagraphStyle('h2',fontName=FONT,fontSize=12,leading=17,textColor=colors.HexColor('#0B7285'),spaceBefore=9,spaceAfter=5,keepWithNext=True)
title_style=ParagraphStyle('title',fontName=FONT,fontSize=22,leading=32,alignment=TA_CENTER,textColor=colors.HexColor('#123B52'),spaceAfter=13)
author_style=ParagraphStyle('author',fontName=FONT,fontSize=10.5,leading=18,alignment=TA_CENTER,textColor=colors.HexColor('#4C6570'))
abs_style=ParagraphStyle('abstract',fontName=FONT,fontSize=9.2,leading=15,alignment=TA_JUSTIFY,textColor=colors.HexColor('#2B3E46'),spaceAfter=5,firstLineIndent=18)
small=ParagraphStyle('small',fontName=FONT,fontSize=7.2,leading=10.4,textColor=colors.HexColor('#263B43'))
ref_style=ParagraphStyle('ref',fontName=FONT,fontSize=7.7,leading=11.5,leftIndent=13,firstLineIndent=-13,spaceAfter=3,textColor=colors.HexColor('#263B43'))
caption=ParagraphStyle('caption',fontName=FONT,fontSize=8,leading=12,alignment=TA_CENTER,textColor=colors.HexColor('#4B626B'),spaceBefore=4,spaceAfter=7)

def page_deco(c,doc):
    c.saveState(); c.setStrokeColor(colors.HexColor('#B4CFD4')); c.setLineWidth(.45); c.line(ML,13*mm,PAGE_W-MR,13*mm)
    c.setFont(FONT,7.2); c.setFillColor(colors.HexColor('#5F7881')); c.drawString(ML,8.5*mm,'城市方舟灾时应急救援基站现实建设技术难题'); c.drawRightString(PAGE_W-MR,8.5*mm,str(doc.page)); c.restoreState()
class Doc(BaseDocTemplate):
    def __init__(self,path):
        super().__init__(path,pagesize=A4,leftMargin=ML,rightMargin=MR,topMargin=MT,bottomMargin=MB,title='城市方舟灾时应急救援基站现实建设技术难题',author='城市方舟项目组',subject='范围综述与系统工程综合')
        self.addPageTemplates(PageTemplate(id='paper',frames=[Frame(ML,MB,PAGE_W-ML-MR,PAGE_H-MT-MB,id='f')],onPage=page_deco))

class Architecture(Flowable):
    def __init__(self): Flowable.__init__(self); self.width=PAGE_W-ML-MR; self.height=82*mm
    def wrap(self,aw,ah): self.width=min(self.width,aw); return self.width,self.height
    def draw(self):
        c=self.canv; w=self.width; layers=[('治理与运营层','指挥｜人员｜流程｜法规｜全寿命运维'),('信息与装备层','通信｜边缘计算｜感知孪生｜空水地无人系统'),('离网生命线层','能源｜供水｜卫生｜通风｜消防｜医疗冷链'),('安全载体层','选址｜结构｜围护｜防洪｜可达与疏散')]; cols=['#E8F4F5','#EEF2F7','#F5F0F8','#F8F3E8']
        y=8*mm; bh=15*mm
        for i,(a,b) in enumerate(reversed(layers)):
            c.setFillColor(colors.HexColor(cols[3-i])); c.setStrokeColor(colors.HexColor('#8DAFB6')); c.roundRect(8*mm,y,w-16*mm,bh,4,fill=1,stroke=1); c.setFillColor(colors.HexColor('#123B52')); c.setFont(FONT,9.5); c.drawString(14*mm,y+9*mm,a); c.setFont(FONT,8); c.setFillColor(colors.HexColor('#4D6872')); c.drawRightString(w-14*mm,y+9*mm,b); y+=17*mm

story=[Spacer(1,8*mm),Paragraph('从微缩概念到现实基站',title_style),Paragraph('“城市方舟”灾时应急救援基站建设的关键技术难题',title_style),Paragraph('——基于36篇文献的范围综述与系统工程综合',author_style),Spacer(1,5*mm),Paragraph('城市方舟项目组　｜　2026年9月',author_style),Spacer(1,8*mm),
Table([[Paragraph('<b>摘要</b>',abs_style),Paragraph('面向城市极端灾害中电力、供水、通信、交通和治理同步失效的情景，本文讨论“城市方舟”灾时应急救援基站从微缩概念模型走向现实建设所必须解决的技术难题。研究对项目提供的36篇PDF文献（共538页）开展语料库范围综述，并以“危险源—功能—设备—接口—失效模式—验证方法”为编码链条进行系统工程综合。结果表明，基站有效性由多灾种选址、灾后可使用结构、离网能源、水与卫生、热环境与医疗、应急通信、感知与数字孪生、空—水—地无人系统、人群疏散、物流治理和全寿命运维共同决定。文献对洪涝风险、基础设施级联、通信和无人系统提供了直接证据，但对结构、微电网、水卫、暖通、医疗和消防的专项证据明显不足。本文提出有效容量木桶模型、四层系统架构、分阶段工程化路线及可证伪的验收试验。',abs_style)]],colWidths=[14*mm,142*mm],style=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F0F7F8')),('BOX',(0,0),(-1,-1),.6,colors.HexColor('#8DB9BF')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)])),Spacer(1,4),Paragraph('<b>关键词：</b>城市方舟；应急救援基站；城市洪涝；关键基础设施；应急通信；无人系统；灾害韧性',abs_style),Spacer(1,4),Paragraph('<b>Abstract:</b> This paper identifies the engineering barriers that must be resolved before the “Urban Ark” can evolve from a miniature concept into a deployable urban emergency-response base. A corpus-based scoping review of 36 project-supplied PDF papers (538 pages) is combined with systems-engineering synthesis. Strong evidence exists for flood risk, cascading infrastructure failure, emergency communications and robotics, while major gaps remain in structural engineering, microgrids, WASH, HVAC, medical continuity and fire safety.',abs_style),PageBreak()]

for title,paras in sections:
    style=h2 if re.match(r'^\d+\.\d+',title) else h1
    story.append(Paragraph(title,style))
    if title.startswith('4 现实'):
        data=[[Paragraph(x,small) for x in ['难题','核心失效','证据','工程响应','来源']]]+[[Paragraph(str(x),small) for x in r] for r in challenge_rows]
        tab=Table(data,colWidths=[22*mm,37*mm,11*mm,65*mm,22*mm],repeatRows=1,hAlign='LEFT')
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0B7285')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,-1),FONT),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#AAC5CA')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F6F7')]),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
        story += [Paragraph('表1　城市方舟建设技术难题、证据等级与验证方向',caption),tab,Spacer(1,7)]
    for p in paras:
        em=re.search(r'\{equation:(.+)\}',p)
        if em:
            before=p[:em.start()]; story.append(Paragraph(cite_pdf(before),body))
            story.append(Paragraph('<i>'+em.group(1).replace('>=','≥')+'</i>',ParagraphStyle('eq',parent=body,alignment=TA_CENTER,firstLineIndent=0,spaceBefore=4,spaceAfter=8)))
        else: story.append(Paragraph(cite_pdf(p),body))
    if title.startswith('5 耦合'):
        story += [Spacer(1,4),Architecture(),Paragraph('图1　城市方舟四层系统架构及功能依赖关系',caption)]



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

story += [CondPageBreak(60*mm),Paragraph('参考文献',h1)]
for i,r in enumerate(refs,1): story.append(Paragraph(f'[{i}] {r}',ref_style))
story += [Spacer(1,8),Paragraph('附注：本文语料边界为项目提供的36篇PDF。条目中个别会议论文或数据库导出文件未含完整卷期页码，均按本地PDF可核验信息著录；正式投稿前应结合目标期刊格式再次校订。',abs_style)]

Doc(str(PDF)).build(story)
r=PdfReader(str(PDF)); txt='\n'.join((p.extract_text() or '') for p in r.pages)
assert len(r.pages)>=10
for token in ['摘要','研究材料与方法','现实建设中的关键技术难题','参考文献','有效容量']:
    assert token in txt,token
assert len(refs)==33
print('PDF',PDF); print('TEX',TEX); print('PAGES',len(r.pages)); print('CHARS',len(txt)); print('REFS',len(refs))
