import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';

const root='F:/gugugaga/07enSimulation/Algorithm_Comparison';
const skill='C:/Users/Lenovo/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const python='C:/Users/Lenovo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const font='Microsoft YaHei';
const ink='#172F3D',muted='#536A76',teal='#007F80',paper='#F6F9FA';
const p=Presentation.create({slideSize:{width:1280,height:720}});
const code='F:/gugugaga/07enSimulation/_v2/Assets/Rescue/Scripts/';
function tx(s,text,x,y,w,h,size=28,color=ink,bold=false){
 const b=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 b.text=text;b.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none'};return b;
}
function slide(title,kicker){const s=p.slides.add();s.background.fill=paper;tx(s,kicker,64,28,1120,30,18,teal,true);tx(s,title,64,72,1152,66,42,ink,true);tx(s,'城市方舟  /  救援船路径规划',64,674,1000,24,16,muted);tx(s,String(p.slides.items.length).padStart(2,'0'),1170,674,48,24,16,muted);return s;}
function notes(s,t){s.speakerNotes.textFrame.setText(t);}
async function img(s,file,x,y,w,h,alt){s.images.add({blob:new Uint8Array(await fs.readFile(file)),contentType:'image/png',alt,fit:'contain',position:{left:x,top:y,width:w,height:h}});}
function table(s,values,top,height,widths,size=24){const t=s.tables.add({rows:values.length,columns:values[0].length,left:64,top,width:1152,height,columnWidths:widths,values});t.styleOptions={headerRow:true,bandedRows:false};t.borders.assign({style:'solid',fill:'#D7E2E6',width:1});t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({margins:{left:16,right:16,top:10,bottom:10},anchor:'center'});for(let r=0;r<values.length;r++){t.rows[r].height=height/values.length;for(let c=0;c<values[0].length;c++){const cell=t.getCell(r,c);cell.fill=r===0?ink:(c===values[0].length-1?'#E8F4F2':'#FFFFFF');cell.text.style={typeface:font,fontSize:size,color:r===0?'#FFFFFF':ink,bold:r===0,autoFit:'none'};}}return t;}

{
const s=slide('面向洪水救援的\nA* 路径规划改进','ALGORITHM COMPARISON');
// Two-line cover title has a dedicated, larger frame.
s.shapes.items[1].position={left:64,top:150,width:680,height:140};
s.shapes.items[1].text.style={typeface:font,fontSize:48,color:ink,bold:true,autoFit:'none'};
tx(s,'传统静态基线 × 当前 Unity 实现',64,326,700,50,30,teal,true);
tx(s,'不仅寻找短路，\n还要判断船能否安全通过。',64,404,620,110,32);
tx(s,'船体约束 · 水深检查 · 逆流代价 · 在线重规划',64,566,1152,45,24,muted);
await img(s,'F:/gugugaga/07enSimulation/_v2/Reports/Model_Previews/RescueBoat.png',750,140,460,405,'项目中的黄色绿色无人救援船模型');
notes(s,'本演示基于当前 Unity 项目源码核对。对比对象是采用距离代价、仅初始规划一次的传统 A* 静态基线，不是宣称所有 A* 系统都缺少动态避障。我们的工作属于面向救援船的工程化扩展，未提出新的启发式函数。代码来源：'+code+'RescueNavigation.cs；'+code+'RescueMission.cs。模型图来自项目 Reports/Model_Previews/RescueBoat.png。');
}
{
const s=slide('A*：用“已走代价 + 剩余估计”寻找路径','01  /  基础原理');
tx(s,'f(n) = g(n) + h(n)',64,172,1152,86,60,teal,true);
tx(s,'g(n)  从起点到当前节点的累计代价',64,286,1130,48,30);
tx(s,'h(n)  当前节点到终点的估计代价',64,346,1130,48,30);
tx(s,'搜索过程',64,432,240,42,28,teal,true);
tx(s,'① 选择 f 最小的节点     ② 检查可通行邻居\n③ 更新代价与父节点     ④ 到达终点后回溯路径',64,488,1152,98,28);
tx(s,'关键澄清：传统 A* 本来就能绕开地图中已知、被标记为不可通行的障碍。',64,613,1152,40,24,teal,true);
notes(s,'A* 是启发式图搜索算法。g 表示已累计的路径代价，h 估计剩余代价，每轮优先扩展 f=g+h 最小的候选节点。适当的启发式和搜索条件下可得到图上的最小代价路径，但不等于真实船舶的全局最优运动轨迹。当前实现采用八邻域栅格、平面欧氏距离启发式，并禁止对角穿越障碍角点。原始文献：Hart, Nilsson, Raphael (1968), A Formal Basis for the Heuristic Determination of Minimum Cost Paths, https://ai.stanford.edu/~nilsson/OnlinePubs-Nils/PublishedPapers/astar.pdf 。实现来源：'+code+'RescueNavigation.cs，Plan、FlatDistance。');
}
{
const s=slide('保留 A* 搜索框架，扩展船舶场景约束','02  /  核心对比');
table(s,[['比较维度','传统静态 A* 基线','当前项目实现'],['障碍信息','初始地图中的静态障碍','静态障碍 + 其他船 / 漂浮物当前位置'],['船体与水深','不额外加入船舶约束','安全占用范围 + 五点水深检查'],['路径代价','几何行驶距离','距离 × 逆流惩罚系数'],['环境更新','首次规划后沿原路径行驶','约每 1.2 秒或路径为空时重规划'],['路径输出','栅格节点序列','通视检查后删去冗余中间点']],171,408,[188,382,582],24);
tx(s,'没有更换：f = g + h；h 仍是平面欧氏距离。',64,603,1152,40,28,teal,true);
notes(s,'表中的传统基线是为了进行实验而明确约定的配置，并非 A* 的能力上限。传统 A* 也可通过地图更新和重复搜索实现动态避障。当前实现额外处理船舶安全占用、水深、逆流成本和当前动态障碍。clearance=0.048m 是静态碰撞检测的水平半宽，并不等价于沿所有船壳点都严格保持 48mm 的净距；其他船中心距离小于 0.096m 时屏蔽节点。源码：'+code+'RescueNavigation.cs（Rebuild、Walkable、DynamicWalkable、Plan、ClearLine）；'+code+'RescueMission.cs（Navigate，planTimer=1.2f）。');
}
{
const s=slide('新障碍出现后，旧路线需要重新计算','03  /  绕障机制示意');
tx(s,'静态、单次规划：旧路线不更新',64,153,552,40,27,muted,true);
tx(s,'当前方案：按更新后的障碍绕行',666,153,550,40,27,teal,true);
await img(s,root+'/assets/Dynamic_Replanning.png',115,198,1050,423,'左右相同地图：旧路线遇到新增漂浮物，重规划路线绕开漂浮物；两种路线都避开已知建筑');
tx(s,'灰虚线：旧路线    青线：更新路线    橙色：新增漂浮物',64,613,1152,32,22,muted);
notes(s,'本页为 AI 生成的机制示意图，不是实测轨迹或 Unity 截图，曲线形状不代表源码中的实际折线路径。两侧地图和原始路线一致，且原始路线本来就绕过已知建筑。左侧特意定义为不重新规划的静态基线，所以新增漂浮物进入原航线后旧路线仍会与其相交；右侧更新不可通行节点并重新运行 A*，路径因此绕行。不能从图中推断原始 A* 不会避障。如果传统 A* 同样更新地图并重规划，也可以绕开新增障碍。当前动态障碍依据当前位置进行检查，不对漂浮物做时空轨迹预测。');
tx(s,'机制示意图，非仿真实测轨迹；对比的是“是否更新并重规划”。',64,647,1152,25,18,teal);
}
{
const s=slide('改进的具体内容：可通行判断与逆流代价','04  /  对应当前代码');
tx(s,'① 先判断：这段水域是否允许船通过',64,165,1152,45,30,teal,true);
tx(s,'静态安全检测半宽 48 mm；船间中心排斥距离 96 mm。\n在中心及四周检测水深：水深 ≥ max(8 mm，吃水 + 1.8 mm)。',64,222,1152,105,27);
tx(s,'② 再比较：相邻节点之间哪条路线代价更低',64,348,1152,45,30,teal,true);
tx(s,'c(i,j) = Δs × [1 + max(0, −v · d) / 0.04]',64,413,1152,65,38,ink,true);
tx(s,'Δs：节点间距    v：当地流速（m/s）    d：行驶方向单位向量',64,492,1152,43,24,muted);
tx(s,'逆流越强，代价越大；顺流不额外奖励。h 仍使用欧氏距离。',64,553,1152,43,27,teal,true);
tx(s,'注意：这是流场加权距离，不是直接计算的能耗或到达时间。',64,618,1152,37,23,muted);
notes(s,'源码逐项对应：Rebuild 使用水平半宽 clearance=.048m 的 OverlapBox 处理静态碰撞；DynamicWalkable 使用 .096m 船中心间距及漂浮物尺寸判断。水深检查涉及中心、正负 x 和正负 z 五个采样点，最低深度为 max(.008, Draft+.0018)，且需要 HasWater。Plan 中代价为 step.magnitude*(1+Max(0,-Dot(flow,step.normalized))/.04)。分母单位 m/s。此代价并非实际功耗模型，不应称作节能最优。示例：逆流方向分量 .02m/s 时系数为1.5，仅为公式演算。尺寸全部为模型尺度，不是实际救援船尺度。静态检测是保守占用近似，可能排除实际可通过的狭窄区域。来源：'+code+'RescueNavigation.cs。');
}
{
const s=slide('路径规划与物理航行，是两层不同的计算','05  /  Unity 仿真实现');
await img(s,'F:/gugugaga/07enSimulation/_v2/Reports/Runtime_Mission_Outbound.png',64,170,718,449,'Unity 救援场景现有运行截图：中心基地、四艘救援船、建筑与水面目标');
tx(s,'规划层',824,172,370,42,30,teal,true);
tx(s,'读取水域与障碍\n运行 A* 并压缩路径\n约每 1.2 秒重新规划',824,229,386,142,27);
tx(s,'运动与避让层',824,396,390,42,30,teal,true);
tx(s,'跟踪航点、差速推进\n短时船间冲突检查\n受水流、阻力和碰撞影响',824,453,386,142,27);
tx(s,'显示的规划线 ≠ 未来真实航迹；实际航迹应单独记录并验证。',64,625,1152,39,26,teal,true);
notes(s,'左图为项目已有运行截图，仅用于说明场景，不作为 A/B 性能证据。来源：Reports/Runtime_Mission_Outbound.png。RescueMission.Navigate 负责航点跟踪与定时重规划；Drive 将控制转换为双推进器控制，物理响应受到水流和阻力等影响。控制层按当前相对位置/速度估计至多1.5秒的船间接近情况，并采用编号优先的避让；这不意味着 A* 已扩展为时空搜索，也不是对漂浮物进行未来轨迹预测。LineRenderer 显示的是规划路径，不是通过动力学前向积分得到的预测轨迹。来源：'+code+'RescueMission.cs。');
}
{
const s=slide('如何证明改进有效：同条件 A/B 对照实验','06  /  验证方案与结论');
table(s,[['测试场景','重点验证','建议记录指标'],['仅有已知静态障碍','两种方案均能绕障','规划耗时、路径长度'],['狭窄通道 / 浅水区域','船体与水深约束是否有效','碰撞次数、搁浅次数、最小净距'],['漂浮物进入原航线','更新路线能否恢复可行','响应时间、重规划次数、到达率'],['相同流场与救援任务','逆流代价是否改善航行','逆流暴露、航时、任务完成率']],166,332,[325,397,430],23);
tx(s,'控制变量：相同地图、起终点、流场、任务和推进控制器。',64,522,1152,39,26,muted);
tx(s,'当前结论：实现了“船舶约束 + 流场代价 + 在线重规划”的 A* 系统。',64,576,1152,44,28,teal,true);
tx(s,'已核实功能差异；尚无同条件 A/B 统计，不宣称提升百分比或全局最优。',64,631,1152,33,23,muted);
notes(s,'本页是待开展的实验设计，不是已完成的实验结果。对照需统一场景、种子、初始船位、救援目标、推进器控制和水流。静态基线定义为只初始规划一次；为了区分在线重规划与代价扩展各自的贡献，建议增加第二个对照：同频率重规划的距离代价 A*；再分别去掉水深、流场和船体约束做消融。记录多个随机种子和重复试验，报告分布和失败情况，而不仅是成功演示。原始A*可在满足条件时求图上最小代价路径，但本系统仍有栅格分辨率、保守占用、动力学跟踪误差以及缺少漂浮物未来预测等限制，不能直接推导真实物理条件下全局最优或现实救援安全保证。');
}
await fs.writeFile(root+'/build/content-notes.txt',p.slides.items.map((s,i)=>'Slide '+(i+1)+'\n'+s.speakerNotes.textFrame.text).join('\n\n'));
const candidate=root+'/build/candidate.pptx';
await (await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:root+'/output/AStar_Algorithm_Comparison.pptx',pythonExecutable:python,integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','3','--require-native-table-slide','7'],requiredNativeTableOwnerSlides:[3,7],fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:root+'/build/validation.json'});
await fs.mkdir(root+'/output/Preview',{recursive:true});
for(let i=0;i<p.slides.items.length;i++){const png=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(root+'/output/Preview/Slide_'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await png.arrayBuffer()));}
console.log('COMPLETE '+root+'/output/AStar_Algorithm_Comparison.pptx');
