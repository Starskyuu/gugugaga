'use strict';
let unity=null;
let latestState=null;
const $=id=>document.getElementById(id);
function command(value){if(unity)unity.SendMessage('RescueWebBridge','Command',value);}
document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>command(button.dataset.command)));
$('speed').addEventListener('change',()=>command('speed:'+$('speed').value));
$('boat').addEventListener('change',()=>command('boat:'+$('boat').value));
$('fullscreen').addEventListener('click',()=>{if(unity)unity.SetFullscreen(1);});
const outcome={Complete:'救援完成',Paused:'已暂停',AutopilotsStopped:'自动驾驶已停止',NoAutonomousBoats:'没有可用自动船',Blocked:'路线受阻',InProgress:'救援进行中'};
window.rescueReceive=value=>{try{const data=JSON.parse(value);latestState=data;$('rescued').textContent=data.rescued+' / '+data.total;$('water').textContent=data.inWater;$('onboard').textContent=data.onboard;$('elapsed').textContent=data.simulationSeconds.toFixed(1)+' s';$('status').textContent=outcome[data.outcome]||data.outcome;}catch(error){console.warn('Telemetry unavailable',error);}};
function fail(message){$('load-message').textContent=message;$('status').textContent='加载失败';$('progress').hidden=true;$('load').hidden=false;$('load').textContent='刷新后重试';$('load').onclick=()=>location.reload();}
$('load').addEventListener('click',async()=>{
 $('load').hidden=true;$('progress').hidden=false;$('status').textContent='正在加载';$('load-message').textContent='正在下载 Unity 场景与物理引擎，请保持页面打开。';
 try{const response=await fetch('simulation/web-config.json');if(!response.ok)throw new Error('场景资源暂不可用');const config=await response.json();
 const script=document.createElement('script');script.src=config.loaderUrl;script.onerror=()=>fail('无法下载仿真程序，请检查网络后重试。');script.onload=async()=>{try{unity=await createUnityInstance($('unity-canvas'),{...config,streamingAssetsUrl:'simulation/StreamingAssets',companyName:'ModelScaleRescue',productName:'City Ark Rescue',productVersion:'Web 1',showBanner:(msg,type)=>{if(type==='error')fail(msg);}},progress=>{$('progress').value=progress;$('load-message').textContent='加载场景 '+Math.round(progress*100)+'%';});$('loading').hidden=true;document.querySelectorAll('button,select').forEach(el=>el.disabled=false);$('status').textContent='已就绪';$('runtime').textContent='Unity WebGL · 模型尺度';}catch(e){fail('无法启动仿真：'+e.message);}};document.body.appendChild(script);
 }catch(e){fail(e.message);}
});
if(document.modelContext?.registerTool){
 const lifetime=new AbortController();window.addEventListener('pagehide',()=>lifetime.abort(),{once:true});
 try{Promise.resolve(document.modelContext.registerTool({name:'read_rescue_status',title:'读取救援仿真状态',description:'读取正在运行的 Unity 救援任务状态和四艘船的遥测，不改变仿真。',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true},execute(input){if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).length)throw new Error('输入必须为空对象');if(!latestState)return {ready:false};return {ready:true,...latestState};}},{signal:lifetime.signal})).catch(()=>{});}catch{}
}
