// Exercise the actual game's Q handler, lock transition and contextual hint.
// Optional HTML argument lets a proposed patch be verified before touching shared source.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[2] || path.join(__dirname,'../belt-runner-3d.html'),'utf8');
const requireMatch = (re,label) => {
  const m=source.match(re); assert.ok(m,'Missing '+label); return m[0];
};
const toggle = requireMatch(/function toggleLock\(\)\{[\s\S]*?\r?\n\}/,'toggleLock');
const name = requireMatch(/const hoverName=[^\r\n]+/,'hoverName');
const keyHandler = requireMatch(/window\.addEventListener\('keydown', e => \{[\s\S]*?\r?\n\}\);/,'keyboard handler');
const hintLine = requireMatch(/  if \(started && !docked && !pilotingCarrier\(\)\)\{[^\r\n]*/,'Q hint');
const hint = hintLine.trimEnd().endsWith('}') ? hintLine : requireMatch(/  if \(started && !docked && !pilotingCarrier\(\)\)\{[^\r\n]*\r?\n[\s\S]*?\r?\n  \}/,'Q hint body');
const rocks=[{name:'Iron Rock'},{name:'Iron Rock'}], raider={}, station={};
const listeners={}; let pointer=null, picks=0;
const c=vm.createContext({
  lock:null, hover:null, lockType:'rock', lockDist:0,
  started:true, paused:false, docked:false, invOpen:false, mapOpen:false,
  keys:{}, CARGO_SHIP:'Cargo ship', toasts:[], segs:[],
  pilotingCarrier:()=>false,
  rockName:r=>r.name,
  hoverPick:()=>{picks++; return pointer;},
  window:{addEventListener:(type,fn)=>{listeners[type]=fn;}}
});
c.toast=(message,bad=false)=>c.toasts.push({message,bad});
vm.runInContext(name+'\n'+toggle+'\n'+keyHandler,c);
function reset(lock=null,hover=null){
  c.lock=lock; c.hover=hover; c.lockType='rock'; c.lockDist=999;
  c.started=true; c.paused=false; c.docked=false; c.toasts=[];
  pointer=hover; picks=0;
}
function press(overrides={}){listeners.keydown({key:'q',repeat:false,target:null,...overrides});}
function prompt(){c.segs=[]; vm.runInContext(hint,c); return c.segs.join('');}
let checks=0;
const targets=[{obj:rocks[0],type:'rock',dist:120,name:'Iron Rock'}, {obj:rocks[1],type:'rock',dist:240,name:'Iron Rock'}, {obj:raider,type:'pirate',dist:360,name:'Raider'}, {obj:station,type:'station',dist:480,name:'Cargo ship'}];
for(const t of targets){
  reset(null,t);
  assert.equal(prompt(),`<kbd>Q</kbd>Lock on ${t.name}`);
  press();
  assert.equal(c.lock,t.obj); assert.equal(c.lockType,t.type); assert.equal(c.lockDist,t.dist);
  checks++;
  for(const old of targets){
    reset(old.obj,t);
    if(old.obj!==t.obj){
      assert.equal(prompt(),`<kbd>Q</kbd>Switch lock to ${t.name}`);
      press();
      assert.equal(c.lock,t.obj,'Q must switch in one press, including two rocks of the same ore');
      assert.equal(c.lockType,t.type); assert.equal(c.lockDist,t.dist);
      assert.equal(c.toasts.length,1); assert.equal(c.toasts[0].message,`Locked on ${t.name}`);
    } else {
      assert.equal(prompt(),'<kbd>Q</kbd>Release lock');
      press(); assert.equal(c.lock,null); assert.equal(c.toasts[0].message,'Lock released');
    }
    checks++;
  }
}
reset(rocks[0],null);
assert.equal(prompt(),'<kbd>Q</kbd>Release lock'); press(); assert.equal(c.lock,null); checks++;
reset(); assert.equal(prompt(),''); press(); assert.equal(c.lock,null);
assert.equal(c.toasts[0].bad,true); checks++;
// A mouse move and Q may arrive before the next animation frame updates the hover label.
reset(rocks[0],targets[0]); pointer=targets[1];
press(); assert.equal(c.lock,rocks[1],'Q must pick at the latest cursor position'); checks++;
reset(rocks[0],targets[1]); pointer=null;
press(); assert.equal(c.lock,null,'A stale hover must not acquire a target after moving away'); checks++;
for(const guard of ['repeat','docked','paused','input']){
  reset(rocks[0],targets[1]);
  if(guard==='docked')c.docked=true;
  if(guard==='paused')c.paused=true;
  press({repeat:guard==='repeat',target:guard==='input'?{tagName:'INPUT'}:null});
  assert.equal(c.lock,rocks[0],guard+' must not change the lock');
  assert.equal(picks,0); checks++;
}
console.log(`PASS ${checks} target-lock cases: acquire, switch, release, fresh cursor, metadata, hints and input guards`);
