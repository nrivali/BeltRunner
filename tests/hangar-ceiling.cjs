const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict'),crypto=require('node:crypto'),vm=require('node:vm');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'assets/cargo_carrier_v3'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const gameFile=path.join(root,'belt-runner-3d.html'),gameSHA=sha(fs.readFileSync(gameFile));
function geometryCheck(name){
 const b=fs.readFileSync(path.join(dir,name)),length=b.readUInt32LE(12),j=JSON.parse(b.subarray(20,20+length).toString());
 const n=j.nodes.find(n=>n.name==='interior'),a=j.accessors[j.meshes[n.mesh].primitives[0].attributes.POSITION],v=j.bufferViews[a.bufferView],start=28+length+(v.byteOffset||0)+(a.byteOffset||0);
 let ceiling=0,coplanar=0;for(let i=0;i<a.count;i++){const o=start+i*(v.byteStride||12),x=b.readFloatLE(o),y=b.readFloatLE(o+4),z=b.readFloatLE(o+8);
  if(Math.abs(Math.abs(x)-420)<.01&&Math.abs(Math.abs(z)-900)<.01){if(Math.abs(y-170)<.01||Math.abs(y-184)<.01)ceiling++;if(Math.abs(y-176)<.01||Math.abs(y-190)<.01)coplanar++;}}
 assert.equal(ceiling,24);assert.equal(coplanar,0);assert.equal(j.images.length,4);
 return {name,sha256:sha(b),ceilingVertices:ceiling,coplanarVertices:coplanar,embeddedImages:j.images.length};
}
const assets=['cargo_carrier.glb','cargo_carrier_assembled.glb'].map(geometryCheck);
const c={window:{}};vm.runInNewContext(fs.readFileSync(path.join(dir,'cargo_carrier_assembled.data.js'),'utf8'),c);assert.equal(sha(Buffer.from(c.window.BeltRunnerCarrierData,'base64')),assets[1].sha256);
const server=http.createServer((req,res)=>{const p=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(!p.startsWith(root+path.sep))return res.writeHead(403).end();fs.readFile(p,(e,b)=>{if(e)return res.writeHead(404).end();res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':'application/octet-stream');res.end(b);});});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl']});
try{
 const page=await browser.newPage({viewport:{width:1000,height:700}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/WebGLProgram|Shader Error/.test(m.text()))errors.push(m.text());});
 await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;let seed=28761;Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};});await page.route(/^https:\/\//,r=>r.abort());
 await page.goto(`http://127.0.0.1:${server.address().port}/belt-runner-3d.html?debug`,{waitUntil:'load',timeout:60000});
 await page.waitForFunction(()=>window.BeltRunner?.carrierAsset.state==='ready'&&BeltRunner.playerAsset.state==='ready',null,{polling:100,timeout:60000});
 const result=await page.evaluate(()=>{
  const b=BeltRunner,V=THREE.Vector3;b.state.tut=-1;b.startGame();b.update(.01);b.updateVisuals(.01,0);document.querySelectorAll('body > :not(canvas):not(script)').forEach(e=>e.style.display='none');
  b.scene.updateMatrixWorld(true);const hull=b.station.getObjectByName('hull'),interior=b.station.getObjectByName('interior'),world=p=>new V(...p).applyQuaternion(b.STATION.q).add(b.STATION.pos),up=new V(0,1,0).applyQuaternion(b.STATION.q),ceilingGaps=[];
  for(const z of [-650,-350,350,650]){
   const ray=new THREE.Raycaster(world([0,0,z]),up,0,250),inner=ray.intersectObject(interior)[0],outer=ray.intersectObject(hull)[0];
   if(!inner||!outer)throw Error('Ceiling surface missing');const gap=outer.distance-inner.distance;
   if(gap<5.9||gap>6.1)throw Error('Ceiling faces overlap: '+gap);ceilingGaps.push(gap);
  }
  let passageRays=0;const model=b.station.getObjectByName('cargo_carrier_model'),solid=['hull','interior','emissive','glass'].map(n=>model.getObjectByName(n));
  for(const x of [-300,0,300])for(const y of [-90,0,90])for(const side of [-1,1]){
   const ray=new THREE.Raycaster(world([x,y,side*1100]),new V(0,0,-side).applyQuaternion(b.STATION.q),0,2200);
   if(ray.intersectObjects(solid,true).length)throw Error('Hangar passage blocked');passageRays++;
  }
  // Facing the ceiling at the game's large world coordinates stresses depth precision.
  // Swapping the draw order must not change which of the two surfaces is visible.
  b.camera.position.copy(world([0,110,500]));b.camera.up.copy(new V(0,0,-1).applyQuaternion(b.STATION.q));b.camera.lookAt(world([0,170,500]));b.camera.updateMatrixWorld(true);
  const draw=()=>{b.lighting.update({camera:b.camera,station:b.station,quality:'balanced',dt:.11});b.renderer.render(b.scene,b.camera);};
  const sample=()=>{draw();const gl=b.renderer.getContext(),p=new Uint8Array(gl.drawingBufferWidth*gl.drawingBufferHeight*4);gl.readPixels(0,0,gl.drawingBufferWidth,gl.drawingBufferHeight,gl.RGBA,gl.UNSIGNED_BYTE,p);return p;};
  const sensitivity=()=>{hull.renderOrder=1;interior.renderOrder=2;const a=sample();hull.renderOrder=2;interior.renderOrder=1;const c=sample();let changed=0;for(let i=0;i<a.length;i+=4)if(Math.max(Math.abs(a[i]-c[i]),Math.abs(a[i+1]-c[i+1]),Math.abs(a[i+2]-c[i+2]))>3)changed++;return changed/(a.length/4);};
  const repairedDrawOrderDifference=sensitivity();if(repairedDrawOrderDifference>.001)throw Error('Ceiling brightness depends on drawing order: '+repairedDrawOrderDifference);
  // Reintroduce the original overlap only in this test to quantify the regression.
  const p=interior.geometry.attributes.position,indices=[];for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);if(Math.abs(Math.abs(x)-420)<.01&&Math.abs(Math.abs(z)-900)<.01&&(Math.abs(y-170)<.01||Math.abs(y-184)<.01))indices.push(i);}
  indices.forEach(i=>p.setY(i,p.getY(i)+6));p.needsUpdate=true;const originalDrawOrderDifference=sensitivity();
  indices.forEach(i=>p.setY(i,p.getY(i)-6));p.needsUpdate=true;hull.renderOrder=interior.renderOrder=0;
  const visits=[];for(let i=0;i<2;i++){
   b.startDeparture();let ticks=0;while(b.cut&&ticks++<400)b.update(.05);if(b.cut||b.flags.docked)throw Error('Departure failed');
   b.startApproach();if(!b.cut)throw Error('Approach failed');ticks=0;while(b.cut&&ticks++<400)b.update(.05);if(b.cut||!b.flags.docked)throw Error('Docking failed');visits.push(b.depotLocal(b.ship.pos).toArray());
  }
  b.updateVisuals(.016,4);b.camera.position.copy(world([0,0,825]));b.camera.up.copy(up);b.camera.lookAt(world([0,0,-600]));b.camera.fov=70;b.camera.updateProjectionMatrix();draw();
  return {ceilingGaps,passageRays,repairedDrawOrderDifference,originalDrawOrderDifference,docking:visits,lights:b.stationPointLights.map(l=>({intensity:l.intensity,visible:l.visible})),triangles:b.carrierAsset.totalTriangles};
 });
 assert.equal(result.triangles,31056);assert.ok(result.docking[0][2]*result.docking[1][2]<0);assert.deepEqual(errors,[]);
 await page.screenshot({path:path.join(dir,'previews/hangar-ceiling-fixed.png')});
 assert.equal(sha(fs.readFileSync(gameFile)),gameSHA,'Shared game changed during validation');assert.equal(sha(fs.readFileSync(path.join(dir,'cargo_carrier_assembled.glb'))),assets[1].sha256);
 const report={passed:true,gameSHA256:gameSHA,assets,scriptFallbackIdentical:true,...result,errors};fs.writeFileSync(path.join(dir,'ceiling-validation.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{await browser.close();server.close();}})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
