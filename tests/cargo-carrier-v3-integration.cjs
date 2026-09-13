const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{const file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}fs.readFile(file,(e,b)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':file.endsWith('.glb')?'model/gltf-binary':'application/octet-stream');res.end(b);});});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const results=[];const crypto=require('node:crypto'),gameFile=path.join(root,'belt-runner-3d.html'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),gameSHA=sha(fs.readFileSync(gameFile));
 try{
  for(const mode of ['http','file','script-fallback','missing','invalid']){
   const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));
   page.on('request',r=>{if(/cargo_carrier.*\.(glb|data\.js)/.test(r.url()))requests.push(r.url());});
   page.on('console',m=>{if(m.type()==='error'&&/WebGLProgram|Shader Error/.test(m.text()))errors.push(m.text());});
   await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;}); // advance simulation explicitly for repeatable checks
   // External fonts are cosmetic; keep this integration test entirely local.
   await page.route(/^https:\/\//,r=>r.abort());
   if(mode==='missing'||mode==='script-fallback')await page.route('**/cargo_carrier_assembled.glb',r=>r.fulfill({status:404,body:'missing'}));
   if(mode==='missing')await page.route('**/cargo_carrier_assembled.data.js',r=>r.fulfill({status:404,body:'missing'}));
   if(mode==='invalid')await page.route('**/cargo_carrier_assembled.glb',r=>r.fulfill({status:200,body:'invalid model'}));
   const url=mode==='file'?pathToFileURL(path.join(root,'belt-runner-3d.html')).href:`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
   await page.goto(url+'?debug',{waitUntil:'load',timeout:60000});
   await page.waitForFunction(()=>window.BeltRunner?.carrierAsset.state!=='loading' && window.BeltRunner?.carrierAsset.state,null,{polling:100,timeout:60000});
   await page.waitForFunction(()=>window.BeltRunner?.playerAsset.state!=='loading',null,{polling:100,timeout:60000});
   const result=await page.evaluate(()=>{
    const b=BeltRunner,a=b.carrierAsset;const model=b.station.getObjectByName('cargo_carrier_model');
    return {state:a.state,error:a.error,revision:a.revision,source:a.source,triangles:a.triangles,meshes:a.meshes,dishMeshes:a.dishMeshes,totalTriangles:a.totalTriangles,model:!!model,engines:b.stationEngines.map(e=>e.position.toArray()),pivot:b.TURRET_PIVOT.toArray(),pads:b.DEPOT.bays.map(v=>v.parkL.toArray()),floor:b.DEPOT.bays[0].y0,fields:b.forceFields.map(f=>f.mesh.parent===b.station),lights:b.stationPointLights.length,anchors:a.anchors&&Object.keys(a.anchors).length,baseColorSize:a.materials&&Object.values(a.materials)[0].map.image.width,hullStations:a.hullShape?.stations.length,normalMaps:a.materials&&Object.values(a.materials).every(m=>m.normalMap?.image.width===2048),drop:b.DROP_PAD.toArray(),playerReady:b.playerAsset.state==='ready'};
   });
   const fallback=mode==='missing'||mode==='invalid';
   assert.equal(result.state,fallback?'fallback':'ready',JSON.stringify(result));
   assert.ok(requests.every(u=>u.includes('/cargo_carrier_v3/')));assert.ok(result.playerReady);
   if(!fallback){
    assert.equal(result.revision,3);assert.equal(result.triangles,28876);assert.equal(result.totalTriangles,31056);assert.equal(result.meshes,4);assert.equal(result.dishMeshes,3);assert.equal(result.anchors,13);assert.ok(result.normalMaps);assert.equal(result.baseColorSize,4096);assert.equal(result.hullStations,18);
    assert.equal(result.source,mode==='file'||mode==='script-fallback'?'script':'glb');
    assert.deepEqual(result.pivot,[-40,995,0]);assert.deepEqual(result.pads.slice().sort((a,b)=>a[2]-b[2]),[[0,-100,-525],[0,-100,525]]);assert.equal(result.lights,2);assert.ok(result.fields.every(Boolean));assert.deepEqual(result.drop,[250,-130,0]);
    assert.deepEqual(result.engines,[[-3580,220,0],[-3580,-140,-470],[-3580,-140,470]]);
    const motion=await page.evaluate(()=>{const b=BeltRunner;const before=b.carrierAsset.anchors.drone_dock_0.clone().applyQuaternion(b.STATION.q).add(b.STATION.pos);return {dockError:before.distanceTo(b.droneDock(0)),parent:b.station.getObjectByName('cargo_carrier_model').parent===b.station};});
    assert.ok(motion.dockError<.001);assert.ok(motion.parent);
    result.rig=await page.evaluate(()=>{
     const b=BeltRunner,rig=b.depotDish,model=b.station.getObjectByName('cargo_carrier_model'),world=p=>new THREE.Vector3(...p).applyQuaternion(b.STATION.q).add(b.STATION.pos);
     if(rig.yaw.parent!==model||model.getObjectByName('cargo_drop_sign_fallback'))throw new Error('Stale carrier geometry');
     const focus=model.getObjectByName('focus'),aim=[];
     for(const point of [[4500,2400,6000],[-4500,3300,-3000],[3500,1200,0]]){
      const target=world(point),want=b.turretAnglesTo(target);Object.assign(b.depotLaser,want);b.updateDepot(0);b.scene.updateMatrixWorld(true);
      const actual=focus.getWorldPosition(new THREE.Vector3()),expected=b.turretMuzzleWorld(want.yaw,want.pitch);
      const dot=new THREE.Vector3(1,0,0).applyQuaternion(rig.pitch.getWorldQuaternion(new THREE.Quaternion())).dot(target.clone().sub(actual).normalize());
      const error=actual.distanceTo(expected);if(error>1e-4||dot<.999999)throw new Error('Dish aim or focus mismatch '+JSON.stringify({error,dot}));aim.push({error,dot});
     }
     const rock=b.asteroids.find(a=>!a.dead&&!a.barren),saved={pos:rock.pos.clone(),hp:rock.hp,level:b.state.depot.laser};
     rock.pos.copy(world([2000,2400,2500]));rock.group.position.copy(rock.pos);rock.group.updateMatrixWorld(true);b.state.depot.laser=3;Object.assign(b.depotLaser,b.turretAnglesTo(rock.pos),{rock,retarget:1});
     for(let i=0;i<10;i++){const aim=rock.asset?b.rockAssets.aimPoint(rock,b.turretMuzzleWorld(b.depotLaser.yaw,b.depotLaser.pitch)):rock.pos;Object.assign(b.depotLaser,b.turretAnglesTo(aim));b.updateDepot(0);}b.updateVisuals(0,2);b.scene.updateMatrixWorld(true);
     if(!b.depotLaser.firing||!b.depotBeam.visible||!rig.rimBeams.every(m=>m.visible))throw new Error('Dish firing effects missing');
     const beamStart=new THREE.Vector3(0,-.5,0).applyMatrix4(b.depotBeam.matrixWorld),beamError=beamStart.distanceTo(focus.getWorldPosition(new THREE.Vector3()));
     if(beamError>1e-4)throw new Error('Beam detached from lens '+beamError);
     for(let i=0;i<6;i++)if(rig.rimGlow[i].getWorldPosition(new THREE.Vector3()).distanceTo(model.getObjectByName('rim_'+i).getWorldPosition(new THREE.Vector3()))>1e-4)throw new Error('Rim effect misplaced');
     rock.pos.copy(saved.pos);rock.group.position.copy(saved.pos);rock.hp=saved.hp;b.state.depot.laser=saved.level;Object.assign(b.depotLaser,{rock:null,firing:false,yaw:0,pitch:.15});b.updateDepot(0);b.updateVisuals(0,3);b.scene.updateMatrixWorld(true);
     const solid=['hull','interior','emissive','glass'].map(n=>model.getObjectByName(n));let clearance=0;
     for(const x of [-300,0,300])for(const y of [-90,0,90])for(const side of [-1,1]){
      const ray=new THREE.Raycaster(world([x,y,side*1100]),new THREE.Vector3(0,0,-side).applyQuaternion(b.STATION.q),0,2200);
      if(ray.intersectObjects(solid,true).length)throw new Error('Carrier passage blocked');clearance++;
     }
     return {aim,beamError,rimEmitters:rig.rimGlow.length,clearance};
    });
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
     assert.ok(result.docking[0][2]*result.docking[1][2]<0);
     result.warp=await page.evaluate(()=>{
      const b=BeltRunner,model=b.station.getObjectByName('cargo_carrier_model'),id=model.uuid,destination=b.ZONES.find(z=>z!==b.zone);
      b.warpTo(destination);for(let i=0;i<1000;i++){b.update(.05);if(i>=200&&b.zone===destination&&b.flags.docked&&!b.cut)break;}b.updateVisuals(0,12);b.scene.updateMatrixWorld(true);
      if(b.zone!==destination||!b.flags.docked||b.cut||model.uuid!==id||model.parent!==b.station)throw new Error('Carrier lost during warp');
      const error=model.getObjectByName('focus').getWorldPosition(new THREE.Vector3()).distanceTo(b.turretMuzzleWorld(b.depotLaser.yaw,b.depotLaser.pitch));
      if(error>1e-4)throw new Error('Dish detached after warp');
      return {zone:b.zone.id,sameModel:true,docked:true,focusError:error,engines:b.stationEngines.length};
     });
     await page.evaluate(()=>{const b=BeltRunner;b.updateVisuals(.016,0);document.querySelectorAll('body > :not(canvas):not(script)').forEach(e=>e.style.display='none');const target=new THREE.Vector3(400,250,0).applyQuaternion(b.STATION.q).add(b.STATION.pos);const offset=new THREE.Vector3(7800,3500,13500).applyQuaternion(b.STATION.q);b.camera.position.copy(b.STATION.pos).add(offset);b.camera.up.copy(new THREE.Vector3(0,1,0).applyQuaternion(b.STATION.q));b.camera.lookAt(target);b.camera.fov=32;b.camera.far=20000000;b.camera.updateProjectionMatrix();b.lighting.update({camera:b.camera,station:b.station,quality:'balanced',dt:.1});b.renderer.render(b.scene,b.camera);});
     const shot=async name=>{const temp=path.join(root,'assets/cargo_carrier_v3/previews',name+'.tmp.png');await page.screenshot({path:temp});fs.renameSync(temp,path.join(root,'assets/cargo_carrier_v3/previews',name+'.png'));};
     await shot('in-game');
     await page.evaluate(()=>{const b=BeltRunner,world=p=>new THREE.Vector3(...p).applyQuaternion(b.STATION.q).add(b.STATION.pos);b.camera.position.copy(world([0,0,825]));b.camera.up.copy(new THREE.Vector3(0,1,0).applyQuaternion(b.STATION.q));b.camera.lookAt(world([0,0,-600]));b.camera.near=1;b.camera.fov=70;b.camera.updateProjectionMatrix();b.lighting.update({camera:b.camera,station:b.station,quality:'balanced',dt:.1});b.renderer.render(b.scene,b.camera);});
     await shot('in-game-hangar');
    }
   } else {assert.equal(result.model,false);await page.evaluate(()=>{BeltRunner.updateVisuals(0,1);BeltRunner.renderer.render(BeltRunner.scene,BeltRunner.camera);});}
   assert.deepEqual(errors,[]);results.push({mode,...result,pageErrors:errors});console.log('PASS '+mode);await page.close();
  }
  fs.writeFileSync(path.join(root,'assets/cargo_carrier_v3/integration-validation.json'),JSON.stringify({gameSHA256:gameSHA,assetSHA256:sha(fs.readFileSync(path.join(root,'assets/cargo_carrier_v3/cargo_carrier_assembled.glb'))),results},null,2));assert.equal(sha(fs.readFileSync(gameFile)),gameSHA,'Shared game changed during testing');console.log(JSON.stringify(results,null,2));
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
