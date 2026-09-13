const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{const file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}fs.readFile(file,(e,b)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':file.endsWith('.glb')?'model/gltf-binary':'application/octet-stream');res.end(b);});});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const results=[];
 try{
  for(const mode of ['http','file','missing']){
   const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;}); // advance simulation explicitly for repeatable checks
   // External fonts are cosmetic; keep this integration test entirely local.
   await page.route(/^https:\/\//,r=>r.abort());
   if(mode==='missing')await page.route('**/cargo_carrier.glb',r=>r.fulfill({status:404,body:'missing'}));
   const url=mode==='file'?pathToFileURL(path.join(root,'belt-runner-3d.html')).href:`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
   await page.goto(url+'?debug',{waitUntil:'load',timeout:60000});
   await page.waitForFunction(()=>window.BeltRunner?.carrierAsset.state!=='loading' && window.BeltRunner?.carrierAsset.state,{timeout:60000});
   const result=await page.evaluate(()=>{
    const b=BeltRunner,a=b.carrierAsset;const model=b.station.getObjectByName('cargo_carrier_model');
    return {state:a.state,error:a.error,triangles:a.triangles,meshes:a.meshes,model:!!model,engines:b.stationEngines.map(e=>e.position.toArray()),pivot:b.TURRET_PIVOT.toArray(),pads:b.DEPOT.bays.map(v=>v.parkL.toArray()),floor:b.DEPOT.bays[0].y0,fields:b.forceFields.map(f=>f.mesh.parent===b.station),lights:b.stationPointLights.length,anchors:a.anchors&&Object.keys(a.anchors).length};
   });
   assert.equal(result.state,mode==='missing'?'fallback':'ready',JSON.stringify(result));
   if(mode!=='missing'){
    assert.equal(result.triangles,38130);assert.equal(result.meshes,4);assert.equal(result.anchors,13);
    assert.deepEqual(result.pivot,[-40,1055,0]);assert.deepEqual(result.pads,[[0,-100,-525],[0,-100,525]]);assert.equal(result.lights,2);assert.ok(result.fields.every(Boolean));
    assert.deepEqual(result.engines,[[-3580,0,-540],[-3580,0,0],[-3580,0,540]]);
    const motion=await page.evaluate(()=>{const b=BeltRunner;const before=b.carrierAsset.anchors.drone_dock_0.clone().applyQuaternion(b.STATION.q).add(b.STATION.pos);return {dockError:before.distanceTo(b.droneDock(0)),parent:b.station.getObjectByName('cargo_carrier_model').parent===b.station};});
    assert.ok(motion.dockError<.001);assert.ok(motion.parent);
    if(mode==='http'){
     result.docking=await page.evaluate(()=>{
      const b=BeltRunner;b.state.tut=-1;b.startGame();const visits=[];
      for(let side=0;side<2;side++){
       b.startDeparture();let ticks=0;while(b.cut&&ticks++<400)b.update(.05);
       if(b.cut||b.flags.docked)throw new Error('Departure did not complete');
       b.startApproach();if(!b.cut)throw new Error('Approach did not start');
       ticks=0;while(b.cut&&ticks++<400)b.update(.05);
       if(b.cut||!b.flags.docked)throw new Error('Docking did not complete');
       const p=b.depotLocal(b.ship.pos);visits.push(p.toArray());
       if(Math.abs(p.y+100)>.1||Math.abs(Math.abs(p.z)-525)>.1)throw new Error('Ship missed raised pad');
      }
      return visits;
     });
     assert.ok(result.docking[0][2]>0 && result.docking[1][2]<0);
     await page.evaluate(()=>{const b=BeltRunner;b.updateVisuals(.016,0);document.querySelectorAll('body > :not(canvas):not(script)').forEach(e=>e.style.display='none');const target=b.STATION.pos.clone();const offset=new THREE.Vector3(9000,5000,14500).applyQuaternion(b.STATION.q);b.camera.position.copy(target).add(offset);b.camera.lookAt(target);b.camera.far=20000000;b.camera.updateProjectionMatrix();b.renderer.render(b.scene,b.camera);});
     await page.screenshot({path:path.join(root,'assets/cargo_carrier/in-game.png')});
    }
   } else assert.equal(result.model,false);
   assert.deepEqual(errors,[]);results.push({mode,...result,pageErrors:errors});await page.close();
  }
  fs.writeFileSync(path.join(__dirname,'carrier-results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
