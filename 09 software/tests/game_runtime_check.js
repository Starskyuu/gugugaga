const fs = require('fs');
const source = fs.readFileSync('rescue_game_ui.py', 'utf8');
const match = source.match(/<script>([\s\S]*)<\/script>/);
if (!match) throw new Error('Game script not found');

const noop = () => {};
const context = new Proxy({}, { get: () => noop, set: () => true });
const elements = new Map();
function element(id) {
  if (!elements.has(id)) {
    elements.set(id, {
      id, value: id === 'algorithm' ? 'balanced' : id === 'speed' ? '6' : '',
      textContent: '', disabled: false, style: {}, selectedOptions: [{ text: '' }],
      classList: { add: noop, remove: noop }, setAttribute: noop,
      addEventListener: noop, setPointerCapture: noop,
      getBoundingClientRect: () => ({ width: 700, height: 700, left: 0, top: 0 }),
      getContext: () => context,
    });
  }
  return elements.get(id);
}
global.document = { getElementById: element };
global.addEventListener = noop;
global.devicePixelRatio = 1;
global.requestAnimationFrame = noop;

const checks = `
function samplePeople(count) {
  const result=[]; let id=1;
  for(let y=.8;y<59.3&&result.length<count;y+=1.05) for(let x=.8;x<59.3&&result.length<count;x+=1.05) {
    const p={id:id++,x,y,rescued:false,boat:0}; if(validPerson(p)) result.push(p);
  }
  if(result.length!==count) throw new Error('Unable to create sample people');
  return result;
}
people=samplePeople(10); planExact();
if(boats.reduce((s,b)=>s+b.assigned,0)!==10) throw new Error('Exact planner lost targets');
people=samplePeople(1000); const started=performance.now(); planBalanced(); const duration=performance.now()-started;
if(boats.reduce((s,b)=>s+b.assigned,0)!==1000) throw new Error('Balanced planner lost targets');
if(!boats.every(b=>b.assigned>0)) throw new Error('A boat received no targets');
console.log(JSON.stringify({exactTargets:10,balancedTargets:1000,balancedPlanMs:Math.round(duration),loads:boats.map(b=>b.assigned)}));
`;

eval(match[1] + checks);

