import fs from 'node:fs/promises';
import { Presentation, PresentationFile } from '@oai/artifact-tool';
const OUT='F:/gugugaga/GPS_YOLO_定位方案.pptx';
async function writeBlob(path, blob){await fs.writeFile(path,new Uint8Array(await blob.arrayBuffer()));}
function box(slide,name,x,y,w,h,fill,line){return slide.shapes.add({geometry:'roundRect',name,position:{left:x,top:y,width:w,height:h},fill,line:{style:'solid',fill:line,width:1.25},borderRadius:'rounded-xl'});}
function text(slide,name,x,y,w,h,value,size,color='#344054',bold=false,alignment='left') {const s=slide.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{style:'solid',fill:'none',width:0}});s.text=value;s.text.style={fontSize:size,color,bold,alignment,fontFace:'Microsoft YaHei',verticalAlignment:'middle'};return s;}
async function main(){
 const p=Presentation.create({slideSize:{width:1280,height:720}}); const s=p.slides.add(); s.background.fill='#FFFFFF';
 s.shapes.add({geometry:'rect',name:'header-rule',position:{left:72,top:128,width:1136,height:2},fill:'#3D8DFF',line:{style:'solid',fill:'#3D8DFF',width:0}});
 text(s,'eyebrow',72,46,380,24,'项目方案梳理',14,'#3D8DFF',true); text(s,'title',72,70,1040,52,'GPS + YOLO 轻量目标定位与反馈系统',38,'#101828',true); text(s,'subtitle',72,142,1110,28,'从视觉识别与坐标输入，到机械响应、通信与高度计算',18,'#667085');
 // Create support and process anchors first; all lines sit behind their labels.
 const research=box(s,'research-support',72,255,40,350,'#F2F7FF','#3D8DFF');
 const input=box(s,'input',128,270,200,114,'#EAF4FF','#3D8DFF'); const hub=box(s,'hub',496,260,232,134,'#FFFFFF','#3D8DFF'); const screen=box(s,'screen',890,222,220,90,'#F7FAFC','#98A2B3'); const mech=box(s,'mech',890,354,220,90,'#F7FAFC','#98A2B3'); const comm=box(s,'comm',470,523,284,80,'#F7FAFC','#98A2B3'); const calc=box(s,'calc',875,523,290,80,'#EEF7FF','#3D8DFF');
 const blue={kind:'straight',line:{style:'solid',fill:'#3D8DFF',width:2},head:{type:'arrow',width:'med',length:'med'}}; const support={kind:'straight',line:{style:'dashed',fill:'#667085',width:1.5},head:{type:'none'}};
 s.shapes.connect(input,hub,{...blue,fromSide:'right',toSide:'left'});s.shapes.connect(hub,screen,{...blue,fromSide:'right',toSide:'left'});s.shapes.connect(hub,mech,{...blue,fromSide:'right',toSide:'left'});s.shapes.connect(hub,comm,{...blue,fromSide:'bottom',toSide:'top',kind:'elbow'});s.shapes.connect(comm,calc,{...blue,fromSide:'right',toSide:'left'});
 s.shapes.connect(research,input,{...support,fromSide:'right',toSide:'left'});s.shapes.connect(research,hub,{...support,fromSide:'right',toSide:'left',kind:'elbow'});s.shapes.connect(research,mech,{...support,fromSide:'right',toSide:'left',kind:'elbow'});s.shapes.connect(research,comm,{...support,fromSide:'right',toSide:'left',kind:'elbow'});s.shapes.connect(research,calc,{...support,fromSide:'right',toSide:'left',kind:'elbow'});
 text(s,'research-text',76,285,32,218,'文\n献\n调\n研',21,'#175CD3',true,'center');text(s,'research-caption',75,518,34,64,'理论\n依据',12,'#667085',false,'center');
 text(s,'input-label',148,286,160,22,'输入层',16,'#3D8DFF',true,'center');text(s,'input-main',144,313,168,28,'GPS 模块 + YOLO',22,'#101828',true,'center');text(s,'input-note',145,345,166,24,'每帧目标识别 / 坐标',15,'#475467',false,'center');
 text(s,'hub-title',520,282,184,30,'ESP32 协调控制',24,'#101828',true,'center');text(s,'hub-note',520,323,184,42,'接收坐标系\n联动 GPIO / 执行单元',16,'#475467',false,'center');text(s,'hub-chip',548,372,130,20,'控制与转发枢纽',13,'#3D8DFF',true,'center');
 text(s,'display-title',912,238,176,24,'屏幕显示',22,'#101828',true,'center');text(s,'display-note',912,270,176,20,'目标状态与坐标',15,'#475467',false,'center');text(s,'mech-title',912,370,176,24,'机械结构',22,'#101828',true,'center');text(s,'mech-note',912,402,176,20,'执行机构 → 高塔',15,'#475467',false,'center');
 text(s,'comm-title',493,539,238,23,'通信：ESP32 mini ↔ 树莓派',19,'#101828',true,'center');text(s,'comm-note',515,569,194,19,'Wi‑Fi 数据交互',15,'#475467',false,'center');text(s,'calc-title',900,539,240,23,'训练与计算：YOLO + 余弦法',19,'#101828',true,'center');text(s,'calc-note',900,569,240,19,'目标小人数据集 → 计算高度',15,'#475467',false,'center');
 text(s,'input-header',128,211,250,28,'01 视觉与定位输入',18,'#101828',true);text(s,'output-header',850,169,280,28,'03 反馈与执行',18,'#101828',true);text(s,'compute-header',470,482,300,28,'02 通信、训练与计算',18,'#101828',true);
 text(s,'support-legend',140,620,350,20,'虚线表示：文献调研提供理论与方案依据',14,'#667085');text(s,'footer',72,666,480,18,'方案概览｜可用于项目汇报与系统设计讨论',12,'#98A2B3');text(s,'footer2',1035,666,173,18,'GPS · YOLO · ESP32',12,'#98A2B3',false,'right');
 await writeBlob('F:/gugugaga/ppt_build/slide-1-with-literature.png',await p.export({slide:s,format:'png',scale:2}));const layout=await s.export({format:'layout'});await fs.writeFile('F:/gugugaga/ppt_build/slide-1-with-literature.layout.json',await layout.text());const out=await PresentationFile.exportPptx(p);await out.save(OUT);
}
main().catch(e=>{console.error(e);process.exitCode=1;});
