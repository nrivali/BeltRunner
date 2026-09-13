const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
require('../assets/cargo_carrier_v3/hull-contact.js');
const b=fs.readFileSync(path.join(__dirname,'../assets/cargo_carrier_v3/cargo_carrier_assembled.glb'));
const json=JSON.parse(b.subarray(20,20+b.readUInt32LE(12)).toString('utf8').trim());
const shape=JSON.parse(json.nodes.find(n=>n.name==='hull_collision_profile').extras.definition),contact=BeltRunnerCarrierHull.contact;
assert.equal(contact({x:3500,y:-500,z:0},20,shape),null,'Rounded bow must not retain the previous box collision');
assert.equal(contact({x:5000,y:0,z:0},20,shape),null);
assert.equal(contact({x:0,y:2000,z:0},20,shape),null);
const stations=shape.stations;let checks=0;
for(let i=0;i<stations.length-1;i++){
  const a=stations[i],b=stations[i+1],x=(a[0]+b[0])/2,w=(a[1]+b[1])/2,h=(a[2]+b[2])/2;
  for(let j=0;j<48;j++){
    const angle=j*Math.PI*2/48,y=h*Math.sign(Math.sin(angle))*Math.abs(Math.sin(angle))**(2/shape.exponent),z=w*Math.sign(Math.cos(angle))*Math.abs(Math.cos(angle))**(2/shape.exponent);
    const result=contact({x,y:y*.95,z:z*.95},24,shape);assert.ok(result);assert.ok([...result.position,...result.normal].every(Number.isFinite));assert.ok(Math.abs(Math.hypot(...result.normal)-1)<1e-6);
    assert.equal(contact({x:result.position[0],y:result.position[1],z:result.position[2]},23.99,shape),null,'Resolved contact must leave the union of hull and engines');checks++;
  }
}
for(const p of [{x:0,y:0,z:0},{x:-3500,y:220,z:0},{x:-3500,y:-140,z:470},{x:-3500,y:40,z:235},{x:-3500,y:40,z:-235},{x:4590,y:0,z:0}]){const c=contact(p,30,shape);assert.ok(c&&c.normal.every(Number.isFinite));assert.equal(contact({x:c.position[0],y:c.position[1],z:c.position[2]},29.99,shape),null);checks++;}
console.log({passed:true,curvedBowFree:true,checks});
