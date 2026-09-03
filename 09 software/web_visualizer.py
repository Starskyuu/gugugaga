"""Zero-dependency browser dashboard for the rescue base station."""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


LOG = logging.getLogger("web_visualizer")


HTML = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>四船协同搜救</title>
<style>
:root{--ink:#17313b;--muted:#60747d;--line:#c8dbe2;--water:#e0f4f8;--panel:#f7fafb;--red:#d9363e}
*{box-sizing:border-box}body{margin:0;font-family:"Microsoft YaHei UI","PingFang SC",sans-serif;color:var(--ink);background:#eef3f5}
header{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 22px;background:#fff;border-bottom:1px solid #d9e3e7}
h1{font-size:21px;margin:0}.summary{font-size:14px;color:var(--muted)}
main{height:calc(100vh - 64px);display:grid;grid-template-columns:minmax(520px,1fr) 320px;gap:12px;padding:12px}
.mapbox,.side{background:#fff;border:1px solid #d6e2e6;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px #2342  }
canvas{display:block;width:100%;height:100%}.side{padding:16px;overflow:auto}.side h2{font-size:15px;margin:2px 0 8px}
.panel{background:var(--panel);border-radius:7px;padding:10px;margin-bottom:16px;font:13px/1.65 Consolas,"Microsoft YaHei UI",monospace;white-space:pre-wrap}
.route{border-left:4px solid var(--c);padding:5px 8px;margin:8px 0;background:#f7fafb;border-radius:0 6px 6px 0;font-size:13px;line-height:1.5}
.buttons{display:grid;grid-template-columns:1fr 1fr;gap:7px}.buttons button{border:0;border-radius:6px;padding:9px 6px;cursor:pointer;background:#e4edf1;color:#17313b;font-weight:600}
.buttons .stop{grid-column:1/-1;background:#c62828;color:#fff}.legend{font-size:12px;line-height:1.8;color:var(--muted);margin-top:12px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:3px}.offline{color:#9aa8ae}.online{color:#14875c}
@media(max-width:850px){header{height:auto;padding:12px;display:block}.summary{margin-top:5px}main{height:auto;min-height:calc(100vh - 80px);grid-template-columns:1fr}.mapbox{height:58vh}.side{overflow:visible}}
</style></head>
<body><header><h1>四船协同搜救实时态势</h1><div id="summary" class="summary">正在连接基站……</div></header>
<main><div class="mapbox"><canvas id="map"></canvas></div><aside class="side">
<h2>船队状态</h2><div id="status" class="panel">等待数据……</div>
<h2>路线分配</h2><div id="routes"></div>
<div class="buttons"><button onclick="action('start-demo')">启动动态演示</button><button onclick="action('replan')">重新规划</button><button onclick="resetMission()">重置任务</button><button class="stop" onclick="stopAll()">全船急停</button></div>
<div class="legend"><span class="dot" style="background:#e53935"></span>待救目标　<span class="dot" style="background:#16a34a"></span>已完成<br>▲ 搜救船　实线：规划路线　虚线：障碍安全区</div>
</aside></main>
<script>
const colors={boat_1:'#1677ff',boat_2:'#00a870',boat_3:'#f59e0b',boat_4:'#8b5cf6'};
let state=null; const canvas=document.getElementById('map'),ctx=canvas.getContext('2d');
function resize(){const r=canvas.getBoundingClientRect(),d=devicePixelRatio||1;canvas.width=r.width*d;canvas.height=r.height*d;ctx.setTransform(d,0,0,d,0,0);if(state)draw(state)}
addEventListener('resize',resize);resize();
function draw(s){state=s;const W=canvas.clientWidth,H=canvas.clientHeight,m=s.map,mw=+m.width_m,mh=+m.height_m,pad=48,sc=Math.min((W-2*pad)/mw,(H-2*pad)/mh),ox=(W-mw*sc)/2,oy=(H-mh*sc)/2;
 const P=(x,y)=>[ox+x*sc,oy+(mh-y)*sc];ctx.clearRect(0,0,W,H);let [x0,y0]=P(0,mh),[x1,y1]=P(mw,0);ctx.fillStyle='#dff3f8';ctx.strokeStyle='#285b6b';ctx.lineWidth=2;ctx.fillRect(x0,y0,x1-x0,y1-y0);ctx.strokeRect(x0,y0,x1-x0,y1-y0);
 let gs=+m.resolution_m;while(gs*sc<18)gs*=2;ctx.strokeStyle='#c4e1e8';ctx.lineWidth=1;for(let x=gs;x<mw;x+=gs){let [px]=P(x,0);line(px,y0,px,y1)}for(let y=gs;y<mh;y+=gs){let [,py]=P(0,y);line(x0,py,x1,py)}
 ctx.fillStyle='#45626d';ctx.font='11px Arial';ctx.textAlign='center';for(let x=0;x<=mw;x++){let [px,py]=P(x,0);ctx.fillText(x+'m',px,py+18)}ctx.textAlign='right';for(let y=0;y<=mh;y++){let [px,py]=P(0,y);ctx.fillText(y+'m',px-8,py+4)}
 const safe=+(m.safety_margin_m||0);for(const r of (m.obstacles||[])){const[a,b,c,d]=r;let [sx1,sy1]=P(Math.max(0,a-safe),Math.min(mh,d+safe)),[sx2,sy2]=P(Math.min(mw,c+safe),Math.max(0,b-safe));ctx.fillStyle='#ffd7a8';ctx.fillRect(sx1,sy1,sx2-sx1,sy2-sy1);ctx.setLineDash([6,4]);ctx.strokeStyle='#d97706';ctx.lineWidth=2;ctx.strokeRect(sx1,sy1,sx2-sx1,sy2-sy1);ctx.setLineDash([]);let [rx1,ry1]=P(a,d),[rx2,ry2]=P(c,b);ctx.fillStyle='#59636b';ctx.fillRect(rx1,ry1,rx2-rx1,ry2-ry1);ctx.strokeStyle='#30363b';ctx.strokeRect(rx1,ry1,rx2-rx1,ry2-ry1)}
 for(const plan of s.plans){if(plan.waypoints.length<2)continue;ctx.beginPath();plan.waypoints.forEach((p,i)=>{let q=P(+p.x,+p.y);i?ctx.lineTo(...q):ctx.moveTo(...q)});ctx.strokeStyle=colors[plan.boat_id]||'#333';ctx.lineWidth=3;ctx.stroke()}
 for(const v of s.victims){let [px,py]=P(+v.x,+v.y);ctx.beginPath();ctx.arc(px,py,9,0,Math.PI*2);ctx.fillStyle=v.completed?'#16a34a':'#e53935';ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.stroke();ctx.fillStyle='#253238';ctx.font='bold 11px "Microsoft YaHei UI"';ctx.textAlign='center';ctx.fillText(v.id,px,py-15);if(v.completed){ctx.fillStyle='#fff';ctx.fillText('✓',px,py+4)}}
 for(const b of s.boats){if(b.x==null)continue;let [px,py]=P(+b.x,+b.y),a=+b.heading,z=15,pts=[[px+Math.cos(a)*z,py-Math.sin(a)*z],[px+Math.cos(a+2.45)*z*.75,py-Math.sin(a+2.45)*z*.75],[px+Math.cos(a-2.45)*z*.75,py-Math.sin(a-2.45)*z*.75]];ctx.beginPath();ctx.moveTo(...pts[0]);ctx.lineTo(...pts[1]);ctx.lineTo(...pts[2]);ctx.closePath();ctx.fillStyle=colors[b.id]||'#333';ctx.fill();ctx.strokeStyle=b.online?'#fff':'#555';ctx.lineWidth=2;ctx.stroke();ctx.fillStyle=colors[b.id]||'#333';ctx.font='bold 12px "Microsoft YaHei UI"';ctx.fillText(b.id,px,py+25)}
 ctx.fillStyle='#285b6b';ctx.font='12px "Microsoft YaHei UI"';ctx.textAlign='left';ctx.fillText('水面坐标：+X →，+Y ↑',x0+8,y0+17);
 if(!s.victims.length&&!s.boats.some(b=>b.x!=null)){ctx.fillStyle='rgba(255,255,255,.88)';ctx.fillRect(W/2-210,H/2-42,420,84);ctx.strokeStyle='#9bb2bb';ctx.strokeRect(W/2-210,H/2-42,420,84);ctx.fillStyle='#334d57';ctx.textAlign='center';ctx.font='bold 16px "Microsoft YaHei UI"';ctx.fillText('尚未收到视觉或动态仿真数据',W/2,H/2-7);ctx.font='13px "Microsoft YaHei UI"';ctx.fillText('运行 start_local_demo.py，或启动真实视觉发送器',W/2,H/2+20)}}
function line(a,b,c,d){ctx.beginPath();ctx.moveTo(a,b);ctx.lineTo(c,d);ctx.stroke()}
function renderText(s){const on=s.boats.filter(b=>b.online).length,done=s.victims.filter(v=>v.completed).length;document.getElementById('summary').textContent=`路径 v${s.path_version} · 在线 ${on}/4 · 已救 ${done}/${s.victims.length} · ${new Date().toLocaleTimeString()}`;
 document.getElementById('status').innerHTML=s.boats.map(b=>`<span class="${b.online?'online':'offline'}">${b.online?'●':'○'}</span> ${b.id.padEnd(7)} ${b.x==null?'未定位':`(${(+b.x).toFixed(2)}, ${(+b.y).toFixed(2)})`} ${b.last_seen_age_s==null?'':(+b.last_seen_age_s).toFixed(1)+'s'}`).join('\n');
 const r=document.getElementById('routes');r.innerHTML=s.plans.length?s.plans.map(p=>`<div class="route" style="--c:${colors[p.boat_id]}"><b>${p.boat_id}</b><br>${p.victim_ids.length?p.victim_ids.join(' → '):'等待'}<br>${(+p.distance_m).toFixed(2)} m / ${(+p.estimated_time_s).toFixed(1)} s</div>`).join(''):'<div class="panel">等待船位、目标和连接……</div>'}
async function poll(){try{const r=await fetch('/api/state',{cache:'no-store'});const s=await r.json();draw(s);renderText(s)}catch(e){document.getElementById('summary').textContent='与基站界面服务断开'}setTimeout(poll,150)}poll();
async function action(name){await fetch('/api/'+name,{method:'POST'})}function resetMission(){if(confirm('清除目标锁定和完成记录？'))action('reset')}function stopAll(){if(confirm('确认立即向所有在线小船发送急停？'))action('emergency-stop')}
</script></body></html>'''


def start_visualizer(station: Any, host: str = "0.0.0.0", port: int = 8080) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/" or self.path.startswith("/index.html"):
                self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path.startswith("/api/state"):
                payload = json.dumps(station.visualization_snapshot(), ensure_ascii=False).encode("utf-8")
                self._send(200, payload, "application/json; charset=utf-8")
            else:
                self._send(404, b"Not found", "text/plain")

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/api/replan":
                station.request_replan()
            elif self.path == "/api/start-demo":
                station.start_demo()
            elif self.path == "/api/reset":
                station.reset_mission()
            elif self.path == "/api/emergency-stop":
                station.emergency_stop("operator_web_gui")
            else:
                self._send(404, b"Not found", "text/plain")
                return
            self._send(200, b'{"ok":true}', "application/json")

        def _send(self, status: int, payload: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            LOG.debug(format, *args)

    server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=server.serve_forever, name="web-visualizer", daemon=True).start()
    return server
