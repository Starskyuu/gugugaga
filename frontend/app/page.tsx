'use client';

import {
  ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Camera, CircleStop, Clock3,
  Radio, RotateCcw, ShieldCheck, Signal, Wifi, WifiOff, Zap,
} from 'lucide-react';
import Image from 'next/image';
import { useCallback, useEffect, useRef, useState } from 'react';

type Command = 'F' | 'B' | 'L' | 'R' | 'S';
type LinkState = 'idle' | 'online' | 'slow' | 'offline';
type LogItem = { id: number; time: string; text: string; tone: 'normal' | 'success' | 'warning' | 'danger' };
type VisionSnapshot = {
  age_ms: number | null;
  coordinate_ready: boolean;
  boats: Array<{ id: number; x: number; y: number; angle: number | null }>;
  persons: Array<{ id: number; x: number; y: number; confidence: number }>;
  performance: { camera_fps?: number; yolo_fps?: number; yolo_ms?: number };
  references: { visible: number; inliers: number; ids: number[] };
  control: { esp32_configured: boolean; ok: boolean | null; latency_ms: number | null; error: string | null };
};

const commandText: Record<Command, string> = { F: '前进', B: '后退', L: '左转', R: '右转', S: '停止' };
const direction = {
  idle: { label: '等待', detail: '等待首次指令', icon: Radio },
  online: { label: '链路正常', detail: '控制指令响应正常', icon: Wifi },
  slow: { label: '链路延迟', detail: '响应较慢，请谨慎操作', icon: Signal },
  offline: { label: '连接中断', detail: '设备无响应，已发出停车', icon: WifiOff },
};

function nowTime() {
  return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(new Date());
}

export default function Home() {
  const [activeCommand, setActiveCommand] = useState<Command | null>(null);
  const [lastCommand, setLastCommand] = useState<Command>('S');
  const [linkState, setLinkState] = useState<LinkState>('idle');
  const [latency, setLatency] = useState<number | null>(null);
  const [clock, setClock] = useState('--:--:--');
  const [serviceInput, setServiceInput] = useState('');
  const [apiBase, setApiBase] = useState('');
  const [visionOnline, setVisionOnline] = useState(false);
  const [videoOnline, setVideoOnline] = useState(false);
  const [vision, setVision] = useState<VisionSnapshot | null>(null);
  const [logs, setLogs] = useState<LogItem[]>([
    { id: 1, time: '--:--:--', text: '控制台已就绪，等待设备指令', tone: 'normal' },
  ]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeRef = useRef<Command | null>(null);
  const requestIdRef = useRef(1);
  const stopLockRef = useRef(false);

  const addLog = useCallback((text: string, tone: LogItem['tone'] = 'normal') => {
    setLogs((items) => [{ id: ++requestIdRef.current, time: nowTime(), text, tone }, ...items].slice(0, 6));
  }, []);

  const sendCommand = useCallback(async (command: Command, quiet = false) => {
    const started = performance.now();
    try {
      const response = await fetch(`${apiBase}/${command}?t=${Date.now()}`, { method: 'GET', cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const acknowledgement = (await response.text()).trim();
      if (acknowledgement !== command) throw new Error('Invalid device acknowledgement');
      const elapsed = Math.round(performance.now() - started);
      setLatency(elapsed);
      setLinkState(elapsed > 350 ? 'slow' : 'online');
      if (!quiet && command !== 'S') addLog(`${commandText[command]}指令已确认 · ${elapsed}ms`, elapsed > 350 ? 'warning' : 'success');
      return true;
    } catch {
      setLatency(null);
      setLinkState('offline');
      if (!quiet) addLog('设备无响应，请检查 Wi-Fi 连接', 'danger');
      return false;
    }
  }, [addLog, apiBase]);

  useEffect(() => {
    const stored = window.localStorage.getItem('rescue-service-url') ?? '';
    const isLocalPreview = ['localhost', '127.0.0.1'].includes(window.location.hostname) && window.location.port === '3000';
    const inferred = window.location.port === '8080'
      ? window.location.origin
      : isLocalPreview
        ? `http://${window.location.hostname}:8080`
        : '';
    const initial = (stored || inferred).replace(/\/$/, '');
    queueMicrotask(() => {
      setServiceInput(initial);
      setApiBase(initial);
    });
  }, []);

  useEffect(() => {
    if (!apiBase) return;
    let alive = true;
    let running = false;
    const refresh = async () => {
      if (running) return;
      running = true;
      try {
        const response = await fetch(`${apiBase}/api/status?t=${Date.now()}`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json() as VisionSnapshot;
        if (!alive) return;
        setVision(data);
        setVisionOnline(data.age_ms !== null && data.age_ms < 2000);
      } catch {
        if (alive) { setVisionOnline(false); setVideoOnline(false); }
      } finally {
        running = false;
      }
    };
    void refresh();
    const poller = window.setInterval(refresh, 500);
    return () => { alive = false; window.clearInterval(poller); };
  }, [apiBase]);

  const connectService = useCallback(() => {
    const normalized = serviceInput.trim().replace(/\/$/, '');
    setApiBase(normalized);
    if (!normalized) { setVisionOnline(false); setVision(null); }
    setVideoOnline(false);
    window.localStorage.setItem('rescue-service-url', normalized);
    addLog(normalized ? `正在连接视觉服务：${normalized}` : '已切换为同源控制模式', 'normal');
  }, [addLog, serviceInput]);

  const clearHeartbeat = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }, []);

  const stopMove = useCallback((reason = '操作员停车') => {
    if (stopLockRef.current) return;
    stopLockRef.current = true;
    window.setTimeout(() => { stopLockRef.current = false; }, 80);
    clearHeartbeat();
    activeRef.current = null;
    setActiveCommand(null);
    setLastCommand('S');
    void sendCommand('S', true);
    addLog(reason, reason.includes('紧急') || reason.includes('失去') ? 'danger' : 'normal');
  }, [addLog, clearHeartbeat, sendCommand]);

  const startMove = useCallback((command: Exclude<Command, 'S'>) => {
    if (activeRef.current === command) return;
    clearHeartbeat();
    activeRef.current = command;
    setActiveCommand(command);
    setLastCommand(command);
    addLog(`开始${commandText[command]} · 松手即停`, 'success');
    void sendCommand(command);
    timerRef.current = setInterval(() => {
      if (activeRef.current) void sendCommand(activeRef.current, true);
    }, 200);
  }, [addLog, clearHeartbeat, sendCommand]);

  useEffect(() => {
    const clockTimer = setInterval(() => setClock(nowTime()), 1000);
    const emergencyStop = () => { if (activeRef.current) stopMove('页面失去焦点，安全停车'); };
    const visibilityStop = () => { if (document.hidden && activeRef.current) stopMove('页面进入后台，安全停车'); };
    const keyDown = (event: KeyboardEvent) => {
      if (event.repeat) return;
      const keys: Record<string, Exclude<Command, 'S'>> = {
        ArrowUp: 'F', w: 'F', W: 'F', ArrowDown: 'B', s: 'B', S: 'B',
        ArrowLeft: 'L', a: 'L', A: 'L', ArrowRight: 'R', d: 'R', D: 'R',
      };
      if (event.code === 'Space') { event.preventDefault(); stopMove('键盘紧急停车'); }
      else if (keys[event.key]) { event.preventDefault(); startMove(keys[event.key]); }
    };
    const keyUp = (event: KeyboardEvent) => {
      const driveKeys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'w', 'W', 'a', 'A', 's', 'S', 'd', 'D'];
      if (driveKeys.includes(event.key) && activeRef.current) { event.preventDefault(); stopMove('方向键松开，安全停车'); }
    };
    window.addEventListener('blur', emergencyStop);
    document.addEventListener('visibilitychange', visibilityStop);
    window.addEventListener('keydown', keyDown);
    window.addEventListener('keyup', keyUp);
    return () => {
      clearInterval(clockTimer); clearHeartbeat();
      window.removeEventListener('blur', emergencyStop);
      document.removeEventListener('visibilitychange', visibilityStop);
      window.removeEventListener('keydown', keyDown);
      window.removeEventListener('keyup', keyUp);
    };
  }, [clearHeartbeat, startMove, stopMove]);

  const controlProps = (command: Exclude<Command, 'S'>) => ({
    onPointerDown: (event: React.PointerEvent<HTMLButtonElement>) => {
      event.preventDefault(); event.currentTarget.setPointerCapture(event.pointerId); startMove(command);
    },
    onPointerUp: (event: React.PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
      stopMove('操作者松手，安全停车');
    },
    onPointerCancel: () => stopMove('触控中断，安全停车'),
    onContextMenu: (event: React.MouseEvent) => event.preventDefault(),
  });

  const link = direction[linkState];

  return (
    <main className="rescue-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><ShieldCheck size={23} strokeWidth={2.2} /></div>
          <div><h1>城市方舟</h1><p>实时搜救控制台</p></div>
        </div>
        <div className="top-status">
          <div className={`link-pill ${linkState}`}><span className="pulse-dot" /><div><strong>{link.label}</strong><small>{latency === null ? '延迟 --' : `延迟 ${latency} ms`}</small></div></div>
          <div className="clock"><Clock3 size={17} /><span>{clock}</span></div>
          <button className="header-stop" onClick={() => stopMove('紧急停车已触发')} aria-label="紧急停车"><CircleStop size={21} fill="currentColor" />紧急停车</button>
        </div>
      </header>

      <section className="workspace">
        <section className="mission-panel">
          <div className="panel-heading"><div><span className="eyebrow">MISSION VIEW</span><h2>任务视野</h2></div><span className="reserved"><Camera size={16} />视频链路预留</span></div>
          <div className="radar-view">
            {apiBase && visionOnline && <Image unoptimized fill sizes="(max-width: 760px) 100vw, 50vw" className={`video-feed ${videoOnline ? 'ready' : ''}`} src={`${apiBase}/video`} alt="搜救摄像头实时标注画面" onLoad={() => setVideoOnline(true)} onError={() => setVideoOnline(false)} />}
            <div className="radar-grid" /><div className="scan-line" />
            {!videoOnline && <div className={`boat ${activeCommand ? 'moving' : ''} direction-${lastCommand}`} aria-label={`当前状态：${commandText[lastCommand]}`}>
              <span className="boat-bow" /><span className="boat-core"><Zap size={20} fill="currentColor" /></span><span className="boat-wake" />
            </div>}
            <div className="direction-readout"><small>当前航行状态</small><strong>{activeCommand ? commandText[activeCommand] : '安全停止'}</strong></div>
            {!videoOnline && <div className="viewport-note"><Camera size={21} /><span>{apiBase ? '正在等待视频流' : '配置树莓派服务地址后'}<br />实时画面将在此显示</span></div>}
          </div>
          <div className="safety-strip"><ShieldCheck size={18} /><span><strong>安全保护已启用</strong>松手停车 · 700ms 超时停车 · 断网停车</span></div>
        </section>

        <aside className="telemetry-panel">
          <div className="panel-heading compact"><div><span className="eyebrow">TELEMETRY</span><h2>设备状态</h2></div></div>
          <div className="service-config">
            <label htmlFor="service-url">树莓派服务地址</label>
            <div><input id="service-url" value={serviceInput} onChange={(event) => setServiceInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') connectService(); }} placeholder="http://192.168.43.10:8080" /><button onClick={connectService}>连接</button></div>
          </div>
          <div className={`connection-card ${visionOnline ? 'online' : apiBase ? 'offline' : 'idle'}`}><div className="connection-icon">{visionOnline ? <Wifi size={24} /> : apiBase ? <WifiOff size={24} /> : <Radio size={24} />}</div><div><strong>{visionOnline ? '视觉服务在线' : apiBase ? '视觉服务无响应' : '等待配置服务'}</strong><p>{visionOnline ? `视觉数据 ${vision?.age_ms ?? 0}ms 前更新` : apiBase ? '请检查树莓派地址和网络' : '输入树莓派 IP 和 8080 端口'}</p></div></div>
          <div className="metric-grid">
            <div className="metric"><span><Camera size={16} />摄像头</span><strong>{visionOnline ? `${vision?.performance.camera_fps?.toFixed(1) ?? '--'} FPS` : '--'}</strong></div>
            <div className="metric"><span><Zap size={16} />YOLO</span><strong>{visionOnline ? `${vision?.performance.yolo_fps?.toFixed(1) ?? '--'} FPS` : '--'}</strong></div>
            <div className="metric"><span><Signal size={16} />参考点</span><strong>{visionOnline ? `${vision?.references.visible ?? 0} 个` : '--'}</strong></div>
            <div className="metric"><span><Radio size={16} />目标</span><strong>{visionOnline ? `${vision?.boats.length ?? 0} 船 / ${vision?.persons.length ?? 0} 人` : '--'}</strong></div>
          </div>
          <div className="log-section">
            <div className="log-title"><span>事件记录</span><button onClick={() => setLogs([])} aria-label="清空记录"><RotateCcw size={14} />清空</button></div>
            <div className="log-list" aria-live="polite">
              {logs.length === 0 ? <p className="empty-log">暂无记录</p> : logs.map((item) => (
                <div className={`log-item ${item.tone}`} key={item.id}><span className="log-dot" /><time>{item.time}</time><p>{item.text}</p></div>
              ))}
            </div>
          </div>
        </aside>

        <section className="control-panel">
          <div className="control-copy"><span className="eyebrow">MANUAL CONTROL</span><h2>航行控制</h2><p>按住移动，松手立即停车</p></div>
          <div className="dpad" aria-label="方向控制区">
            <button className={`drive-btn forward ${activeCommand === 'F' ? 'active' : ''}`} {...controlProps('F')} aria-label="按住前进"><ArrowUp size={31} /><span>前进</span><kbd>W</kbd></button>
            <button className={`drive-btn left ${activeCommand === 'L' ? 'active' : ''}`} {...controlProps('L')} aria-label="按住左转"><ArrowLeft size={31} /><span>左转</span><kbd>A</kbd></button>
            <button className="center-stop" onPointerDown={(event) => { event.preventDefault(); stopMove('紧急停车已触发'); }} aria-label="停止"><CircleStop size={30} fill="currentColor" /><span>STOP</span></button>
            <button className={`drive-btn right ${activeCommand === 'R' ? 'active' : ''}`} {...controlProps('R')} aria-label="按住右转"><ArrowRight size={31} /><span>右转</span><kbd>D</kbd></button>
            <button className={`drive-btn backward ${activeCommand === 'B' ? 'active' : ''}`} {...controlProps('B')} aria-label="按住后退"><ArrowDown size={31} /><span>后退</span><kbd>S</kbd></button>
          </div>
          <div className="keyboard-hint">键盘支持 WASD / 方向键 · 空格急停</div>
        </section>
      </section>
    </main>
  );
}
