// Run with: node tests/rock-collision-grid.cjs
const assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path'), vm=require('node:vm');
const Grid=require('../assets/asteroids_v2/collision-grid.js');
const THREE=require('../vendor/three-r158/three.min.js');
const source=fs.readFileSync(path.join(__dirname,'../belt-runner-3d.html'),'utf8');
let seed=71239;
const random=()=>{ seed=(1664525*seed+1013904223)>>>0; return seed/4294967296; };
const vector=(x=0,y=0,z=0)=>new THREE.Vector3(x,y,z);
const rock=(id,r,x,y=0,z=0,free=false)=>({id,r,pos:vector(x,y,z),vel:vector(),free,field:null});
const grid=new Grid(), out=[];
const rocks=Array.from({length:2400},(_,i)=>rock(i,8*Math.pow(2500,random()),(random()-.5)*200000,(random()-.5)*30000,(random()-.5)*200000));
rocks.push(rock(2400,199,-1200),rock(2401,200,-.00001),rock(2402,500,1200),rock(2403,25000,80000));
grid.rebuild(rocks);
let queries=0;
function checkQuery(pos,radius){
  // Exhaustive sphere search is independent of the grid's level/cell traversal.
  const expected=rocks.filter(a=>pos.distanceToSquared(a.pos)<=Math.pow(radius+3*a.r+4,2)).map(a=>a.id).sort((a,b)=>a-b);
  const result=grid.query(pos,radius,out).map(a=>a.id).sort((a,b)=>a-b);
  assert.deepEqual(result,expected); assert.equal(new Set(result).size,result.length); queries++;
}
for(let i=0;i<350;i++) checkQuery(vector((random()-.5)*200000,(random()-.5)*30000,(random()-.5)*200000),i%4===0?1:Math.pow(random(),3)*80000);
for(const a of rocks.slice(-4)) checkQuery(a.pos,3*a.r+4);
// Corrections can cross positive/negative cell boundaries or change size class.
for(let i=0;i<100;i++){
  const a=rocks[i]; a.pos.set(-2400+i*.01,1200-i*.01,4800+i*11); a.r=i%2?15000:12; grid.update(a);
  checkQuery(a.pos,3*a.r+4);
}
grid.rebuild(rocks.slice(0,3));
assert.deepEqual(grid.query(vector(),1e9,out).map(a=>a.id).sort((a,b)=>a-b),[0,1,2]);
grid.clear(); assert.equal(grid.query(vector(),1e9,out).length,0);

const collisionCode=source.slice(source.indexOf('function rockPair(a, b){'),source.indexOf('// Rocks ride their orbit rails'));
function runtime(list,debris=[]){
  const context={nearRocks:list,debris,rockCollisionGrid:new Grid(),rockCandidates:[],tmpN:vector(),
    radiusAlong:a=>a.surfaceR||a.r,
    setAdrift:a=>{ if(!a.free){ a.free=true; a.vel=vector(); a.field=null; } }};
  vm.createContext(context); vm.runInContext(collisionCode,context); return context;
}
const clone=a=>({...a,pos:a.pos.clone(),vel:a.vel.clone()});
const snapshot=items=>items.map(a=>({id:a.id,pos:a.pos.toArray(),vel:a.vel.toArray(),free:a.free}));
let responseCases=0;
for(const [r1,r2,position] of [[30,40,1199],[40,1600,-1201],[1800,2400,9600],[12000,25,-24000]]){
  for(const moving of ['first','second','both']){
    const a=rock(1,r1,position,0,0,moving!=='second'),b=rock(2,r2,position+r1+r2-5,0,0,moving!=='first');
    a.vel.x=20; b.vel.x=-10;
    const actual=[a,b],expected=actual.map(clone), direct=runtime(expected);
    direct.rockPair(expected[0],expected[1]); runtime(actual).collideRocks();
    for(let i=0;i<2;i++){
      assert(actual[i].pos.distanceTo(expected[i].pos)<1e-8);
      assert(actual[i].vel.distanceTo(expected[i].vel)<1e-8);
      assert.equal(actual[i].free,expected[i].free);
    }
    responseCases++;
  }
}
// No drifting rocks: no candidate search, index construction or pair callbacks.
const passive=rocks.map(a=>({...a,free:false})), idle=runtime(passive);
idle.rockPair=()=>assert.fail('Passive rock pair was tested'); idle.collideRocks();
assert.equal(idle.rockCollisionGrid.entries.size,0); assert.equal(idle.rockCollisionGrid.stats.queries,0);
// Exhaustive moving-pair oracle, with non-mutating callbacks to isolate coverage.
const mixed=rocks.slice(0,600).map((a,i)=>({...a,free:i%19===0})), pairs=new Set(), collision=runtime(mixed);
collision.rockPair=(a,b)=>{
  assert(a.free||b.free); const key=[a.id,b.id].sort((a,b)=>a-b).join(':');
  assert(!pairs.has(key),'Duplicate pair '+key); pairs.add(key);
};
collision.collideRocks(); let requiredPairs=0;
for(let i=0;i<mixed.length;i++) for(let j=i+1;j<mixed.length;j++){
  const a=mixed[i],b=mixed[j];
  if((a.free||b.free) && a.pos.distanceToSquared(b.pos)<=Math.pow(3*(a.r+b.r),2)){
    assert(pairs.has([a.id,b.id].sort((a,b)=>a-b).join(':'))); requiredPairs++;
  }
}
// Debris still bounces off a stationary colossal with no drifting rocks present.
const boulder=rock(7,1800,-1200), chunk={pos:vector(601,0,0),r:10,vel:vector(-20,0,0),spin:.1};
const expectedChunk={...chunk,pos:chunk.pos.clone(),vel:chunk.vel.clone()};
runtime([clone(boulder)]).chunkRock(expectedChunk,boulder);
runtime([boulder],[chunk]).collideRocks();
assert(chunk.pos.distanceTo(expectedChunk.pos)<1e-9); assert(chunk.vel.distanceTo(expectedChunk.vel)<1e-9); assert.equal(chunk.spin,expectedChunk.spin);
assert.equal(boulder.free,false);
console.log(JSON.stringify({passed:true,exhaustiveQueries:queries,impactResponseCases:responseCases,requiredMovingPairs:requiredPairs,uniqueCandidates:pairs.size,idleQueries:0,debrisBounce:true}));
