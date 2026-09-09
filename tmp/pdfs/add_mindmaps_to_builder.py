from pathlib import Path

p = Path(r"F:\gugugaga\tmp\pdfs\build_city_ark_pdf.py")
s = p.read_text(encoding="utf-8")
s = s.replace("Table, TableStyle, KeepTogether\n", "Table, TableStyle, KeepTogether, Flowable\n")

insert = r'''

MINDMAPS = {
"0":("核心结论",[("任务边界","人群·半径·时长"),("复合灾害","级联·共因失效"),("离网生命线","电·水·通信"),("平灾转换","快速启动·可降级"),("运营治理","责任·法规·经费"),("验证闭环","演练·故障注入")]),
"1":("定义城市方舟",[("系统定位","韧性社区节点"),("服务对象","常住·流动·弱势"),("服务模式","避险·安置·转运"),("自持能力","24/72小时·7天"),("最低服务","水电卫医通信"),("有效容量","取最弱子系统")]),
"2":("十五类技术难题",[("风险与场地","多灾种·选址·结构"),("生命线","能源·水·卫生"),("环境安全","通风·消防·感染"),("信息医疗","通信·分诊·连续照护"),("物流与人群","库存·无障碍·安保"),("长期可用","控制·运维·法规")]),
"3":("危险耦合关系",[("电力","泵·通信·通风·冷链"),("洪水","机房共因失效"),("热环境","健康·冲突·医疗"),("卫生","容量·感染·秩序"),("道路通信","补给·转运·调度"),("人员供应商","启动·维修·替代")]),
"4":("技术优先级",[("P0 定义","任务·风险·容量"),("P0 治理","主体·法规·选址"),("P1 安全","结构·能源·水卫"),("P1 连续","通风·通信·医疗"),("P2 复制","模块·接口·网络"),("P2 持续","运维·成本·公平")]),
"5":("最小可行基站",[("A 需求冻结","场景·服务·状态"),("B 数字样机","模型·台架·接口"),("C 功能舱","1:1部署与人因"),("D 整站试点","满载·故障注入"),("E 网络复制","分级站型·互援"),("阶段门槛","证据通过再推进")]),
"6":("验证试验",[("生命线中断","断电·断网·断水"),("容量极限","满员·热湿·物耗"),("故障注入","单点·共因·攻击"),("人员情景","减员·夜间·疲劳"),("人群情景","无障碍·冲突·团聚"),("通过标准","安全·功能·恢复")]),
"7":("100分检查表",[("需求风险 20","人群·场景·恢复"),("工程系统 30","结构·能源·水卫"),("服务人因 20","流程·无障碍·照护"),("运营持续 20","责任·经费·库存"),("验证改进 10","带载·故障·复验"),("决策规则","低于70分不深化")]),
"8":("研究与数据采集",[("人群与灾害","画像·气候·地质"),("生命线","中断时长·空间相关"),("工程实测","负荷·水耗·物耗"),("运营资源","人员·医院·物流"),("供应与成本","交期·替代·全寿命"),("现场验证","访谈·人群试验")]),
"9":("微缩模型反向要求",[("场地网络","风险·双路径·节点"),("空间流线","洁污·人货废分离"),("生命线","电水通信独立路径"),("模式转换","平时·灾时·最低"),("无障碍安全","担架·消防·疏散"),("故障表达","旁路·替代·降级")]),
"10":("文献校核追溯",[("建立台账","题名·方法·局限"),("难题映射","十五类逐篇对应"),("证据分级","实证·仿真·建议"),("适用条件","气候·人群·规范"),("冲突空白","不平均·补现场数据"),("决策追踪","论断→验证→状态")]),
"11":("下一步行动",[("冻结任务","城市·人群·灾种"),("比较地块","风险·路网·人口"),("统一容量","水电卫通风人员"),("失效工作坊","接口·共因风险"),("首批原型","能源·水卫·通信"),("运营闭环","预算·演练·评分")]),
}

class MindMap(Flowable):
    def __init__(self, chapter, center, branches):
        Flowable.__init__(self); self.chapter=chapter; self.center=center; self.branches=branches
        self.width=PAGE_W-MARGIN_L-MARGIN_R; self.height=82*mm
    def wrap(self, aw, ah): self.width=min(self.width,aw); return self.width,self.height
    def _lines(self,t,n=8): return [t[i:i+n] for i in range(0,len(t),n)] or [""]
    def _node(self,c,x,y,w,h,title,detail,fill,stroke):
        c.setFillColor(fill); c.setStrokeColor(stroke); c.setLineWidth(.8); c.roundRect(x,y,w,h,4,fill=1,stroke=1)
        ls=self._lines(title,9)+self._lines(detail,11); ntitle=len(self._lines(title,9)); yy=y+h/2+(len(ls)-1)*5
        for j,line in enumerate(ls):
            c.setFont(FONT,8.5 if j<ntitle else 7.2); c.setFillColor(colors.HexColor("#163D4A") if j<ntitle else colors.HexColor("#4B6973")); c.drawCentredString(x+w/2,yy,line); yy-=10
    def draw(self):
        c=self.canv; w,h=self.width,self.height; c.setFillColor(colors.HexColor("#F7FBFB")); c.roundRect(0,0,w,h,6,fill=1,stroke=0)
        c.setFillColor(colors.HexColor("#607D86")); c.setFont(FONT,7.5); c.drawString(6,h-12,f"图 {self.chapter}  章节思维导图")
        cw,ch=42*mm,20*mm; cx,cy=(w-cw)/2,(h-ch)/2; nw,nh=47*mm,16*mm; ys=[h-27*mm,h/2-nh/2,11*mm]; lx,rx=7*mm,w-7*mm-nw
        pts=[]
        for i in range(6):
            x=lx if i<3 else rx; y=ys[i if i<3 else i-3]; pts.append((x+nw/2,y+nh/2))
        c.setStrokeColor(colors.HexColor("#79ADB5")); c.setLineWidth(1.2)
        for ex,ey in pts:
            sx=cx if ex<w/2 else cx+cw; sy=cy+ch/2; bend=(sx+ex)/2; c.line(sx,sy,bend,sy); c.line(bend,sy,bend,ey); c.line(bend,ey,ex,ey)
        self._node(c,cx,cy,cw,ch,self.center,f"第{self.chapter}章",colors.HexColor("#CFECEE"),colors.HexColor("#0B7285"))
        fs=[colors.HexColor("#E8F4F5"),colors.HexColor("#EEF4FA"),colors.HexColor("#F4F0FA")]
        for i,((title,detail),(ex,ey)) in enumerate(zip(self.branches,pts)):
            x=lx if i<3 else rx; y=ys[i if i<3 else i-3]; self._node(c,x,y,nw,nh,title,detail,fs[i%3],colors.HexColor("#9EBEC4"))
'''

needle = "def esc(s):\n"
if "class MindMap" not in s:
    s = s.replace(needle, insert + "\n" + needle)

old = '''    elif raw.startswith("## "):
        story.append(Paragraph(inline(raw[3:]), S["h2"]))'''
new = '''    elif raw.startswith("## "):
        heading = raw[3:]
        story.append(Paragraph(inline(heading), S["h2"]))
        mm = re.match(r"^(\\d+)\\.", heading)
        if mm and mm.group(1) in MINDMAPS:
            chapter = mm.group(1); center, branches = MINDMAPS[chapter]
            story += [MindMap(chapter, center, branches), Spacer(1, 7)]'''
if "chapter = mm.group(1)" not in s:
    if old not in s: raise RuntimeError("heading insertion point not found")
    s = s.replace(old,new)
p.write_text(s,encoding="utf-8")
print("mind maps inserted")
