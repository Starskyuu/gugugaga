import fs from 'node:fs/promises';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const OUT = 'F:/gugugaga/GPS_YOLO_定位方案.pptx';
const PREVIEW = 'F:/gugugaga/ppt_build/slide-1.png';
const LAYOUT = 'F:/gugugaga/ppt_build/slide-1.layout.json';

async function writeBlob(file, blob) {
  await fs.writeFile(file, new Uint8Array(await blob.arrayBuffer()));
}

function addBox(slide, name, x, y, w, h, text, opts = {}) {
  const s = slide.shapes.add({
    geometry: opts.geometry || 'roundRect', name,
    position: { left: x, top: y, width: w, height: h },
    fill: opts.fill || '#FFFFFF',
    line: { style: 'solid', fill: opts.line || '#B8BCC4', width: opts.lineWidth || 1.25 },
    borderRadius: opts.radius || 'rounded-xl',
  });
  s.text = text;
  s.text.style = {
    fontSize: opts.fontSize || 19, color: opts.color || '#101828',
    bold: opts.bold ?? false, alignment: opts.alignment || 'center',
    fontFace: 'Microsoft YaHei', verticalAlignment: 'middle'
  };
  return s;
}

function addText(slide, name, x, y, w, h, text, opts = {}) {
  const s = slide.shapes.add({ geometry: 'textbox', name, position: { left:x, top:y, width:w, height:h }, fill:'none', line:{style:'solid', fill:'none', width:0} });
  s.text = text;
  s.text.style = { fontSize: opts.fontSize || 18, color: opts.color || '#344054', bold: opts.bold || false, alignment: opts.alignment || 'left', fontFace:'Microsoft YaHei', verticalAlignment:'middle' };
  return s;
}

async function main() {
  const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  const slide = p.slides.add();
  slide.background.fill = '#FFFFFF';

  // Background structure
  const rule = slide.shapes.add({ geometry:'rect', name:'header-rule', position:{left:72,top:128,width:1136,height:2}, fill:'#3D8DFF', line:{style:'solid',fill:'#3D8DFF',width:0} });
  addText(slide,'eyebrow',72,46,380,24,'项目方案梳理', {fontSize:14,color:'#3D8DFF',bold:true});
  addText(slide,'title',72,70,1040,52,'GPS + YOLO 轻量目标定位与反馈系统', {fontSize:38,color:'#101828',bold:true});
  addText(slide,'subtitle',72,142,1110,28,'从视觉识别与坐标输入，到机械响应、通信与高度计算', {fontSize:18,color:'#667085'});

  // connectors are created before the nodes so they remain behind labels
  const sourceAnchor = addBox(slide,'source-anchor',118,270,210,114,'', {fill:'#EAF4FF',line:'#3D8DFF'});
  const hubAnchor = addBox(slide,'hub-anchor',496,260,232,134,'', {fill:'#FFFFFF',line:'#3D8DFF',lineWidth:2});
  const outputAnchor = addBox(slide,'output-anchor',890,222,220,90,'', {fill:'#F7FAFC',line:'#98A2B3'});
  const mechAnchor = addBox(slide,'mech-anchor',890,354,220,90,'', {fill:'#F7FAFC',line:'#98A2B3'});
  const commAnchor = addBox(slide,'comm-anchor',470,523,284,80,'', {fill:'#F7FAFC',line:'#98A2B3'});
  const calcAnchor = addBox(slide,'calc-anchor',875,523,290,80,'', {fill:'#EEF7FF',line:'#3D8DFF'});

  const arrow = {kind:'straight',line:{style:'solid',fill:'#3D8DFF',width:2},head:{type:'arrow',width:'med',length:'med'}};
  slide.shapes.connect(sourceAnchor, hubAnchor, {...arrow,fromSide:'right',toSide:'left'});
  slide.shapes.connect(hubAnchor, outputAnchor, {...arrow,fromSide:'right',toSide:'left'});
  slide.shapes.connect(hubAnchor, mechAnchor, {...arrow,fromSide:'right',toSide:'left'});
  slide.shapes.connect(hubAnchor, commAnchor, {...arrow,fromSide:'bottom',toSide:'top',kind:'elbow'});
  slide.shapes.connect(commAnchor, calcAnchor, {...arrow,fromSide:'right',toSide:'left'});

  // Node overlays
  addText(slide,'input-kicker',138,286,170,22,'输入层', {fontSize:16,color:'#3D8DFF',bold:true,alignment:'center'});
  addText(slide,'input-main',134,313,178,28,'GPS 模块 + YOLO', {fontSize:23,color:'#101828',bold:true,alignment:'center'});
  addText(slide,'input-note',137,345,172,24,'每帧目标识别 / 坐标', {fontSize:15,color:'#475467',alignment:'center'});

  addText(slide,'hub-title',520,282,184,30,'ESP32 协调控制', {fontSize:24,color:'#101828',bold:true,alignment:'center'});
  addText(slide,'hub-note',520,323,184,42,'接收坐标系\n联动 GPIO / 执行单元', {fontSize:16,color:'#475467',alignment:'center'});
  addText(slide,'hub-chip',548,372,130,20,'控制与转发枢纽', {fontSize:13,color:'#3D8DFF',bold:true,alignment:'center'});

  addText(slide,'display-title',912,238,176,24,'屏幕显示', {fontSize:22,color:'#101828',bold:true,alignment:'center'});
  addText(slide,'display-note',912,270,176,20,'目标状态与坐标', {fontSize:15,color:'#475467',alignment:'center'});
  addText(slide,'mech-title',912,370,176,24,'机械结构', {fontSize:22,color:'#101828',bold:true,alignment:'center'});
  addText(slide,'mech-note',912,402,176,20,'执行机构 → 高塔', {fontSize:15,color:'#475467',alignment:'center'});

  addText(slide,'comm-title',493,539,238,23,'通信：ESP32 mini ↔ 树莓派', {fontSize:19,color:'#101828',bold:true,alignment:'center'});
  addText(slide,'comm-note',515,569,194,19,'Wi‑Fi 数据交互', {fontSize:15,color:'#475467',alignment:'center'});
  addText(slide,'calc-title',900,539,240,23,'训练与计算：YOLO + 余弦法', {fontSize:19,color:'#101828',bold:true,alignment:'center'});
  addText(slide,'calc-note',900,569,240,19,'目标小人数据集 → 计算高度', {fontSize:15,color:'#475467',alignment:'center'});

  // Side explanation
  addText(slide,'left-label',80,211,280,28,'01 视觉与定位输入', {fontSize:18,color:'#101828',bold:true});
  addText(slide,'right-label',850,169,280,28,'03 反馈与执行', {fontSize:18,color:'#101828',bold:true});
  addText(slide,'bottom-label',470,482,290,28,'02 通信、训练与计算', {fontSize:18,color:'#101828',bold:true});

  addText(slide,'footer',72,666,480,18,'方案概览｜可用于项目汇报与系统设计讨论', {fontSize:12,color:'#98A2B3'});
  addText(slide,'footer2',1035,666,173,18,'GPS · YOLO · ESP32', {fontSize:12,color:'#98A2B3',alignment:'right'});

  const png = await p.export({slide,format:'png',scale:2});
  await writeBlob(PREVIEW,png);
  const layout = await slide.export({format:'layout'});
  await fs.writeFile(LAYOUT,await layout.text());
  const pptx = await PresentationFile.exportPptx(p);
  await pptx.save(OUT);
}
main().catch(err=>{ console.error(err); process.exitCode=1; });
