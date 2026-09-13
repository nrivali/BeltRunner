// Browser validation of the actual Blender asset, Hub lifecycle, traffic pads and visual preview.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'assets/colony_garden'),file=path.join(root,'belt-runner-3d.html'),source=fs.readFileSync(file,'utf8'),mode=process.argv[2]||'http';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const instrument='Object.assign(window.BeltRunner,{HOLD,COLONY,BERTHS,holdAtColony,colonyCollide,startHoldApproach,setTestDocked:v=>{docked=v;},rockCollisionGrid,';
const server=http.createServer((req,res)=>{
  const p=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
  if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  if(p===file){res.setHeader('Content-Type','text/html; charset=utf-8');res.end(source.replace('Object.assign(window.BeltRunner,{rockCollisionGrid,',instrument));return;}
  fs.readFile(p,(e,b)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',p.endsWith('.html')?'text/html':p.endsWith('.js')?'text/javascript':p.endsWith('.png')?'image/png':'application/octet-stream');res.end(b);});
});
(async()=>{let browser;try{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/Shader|WebGLProgram/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;let s=571;Math.random=()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296;};});
  if(mode==='script'||mode==='missing')await page.route('**/colony_garden/garden-habitat.glb',r=>r.fulfill({status:404,body:'missing'}));
  if(mode==='missing')await page.route('**/colony_garden/garden-habitat.data.js',r=>r.fulfill({status:404,body:'missing'}));
  const url=mode==='file'?require('node:url').pathToFileURL(file).href:base+'/belt-runner-3d.html';
  await page.goto(url+'?debug',{waitUntil:'load',timeout:60000});
  await page.waitForFunction(()=>window.BeltRunner?.rockAssets.ready&&BeltRunner.carrierAsset.state==='ready',null,{timeout:90000,polling:100});
  const setup=await page.evaluate(async()=>{
    const b=BeltRunner;b.loadZone(b.ZONES.find(z=>z.hub));await Promise.all([b.colony.assetReady,b.planets[0].assetReady]);
    window.drawColony=(name='overview')=>{
      [...document.querySelectorAll('body > :not(canvas):not(script)')].forEach(e=>e.style.display='none');
      b.camera.fov=42;b.camera.updateProjectionMatrix();
      if(name==='overview'){b.camera.position.set(-76000,72000,120000);b.camera.lookAt(0,3000,0);}
      if(name==='gardens'){b.colony.ring.rotation.y=0;b.camera.position.set(-30000,14000,65000);b.camera.lookAt(-20500,1500,47500);}
      if(name==='berths'){b.camera.position.set(-14000,18000,24000);b.camera.lookAt(0,12000,3200);}
      b.camera.updateMatrixWorld(true);b.lighting.update({camera:b.camera,station:b.station,quality:'balanced',dt:.2});b.rockAssets.render(b.camera,'balanced');b.renderer.render(b.scene,b.camera);
      return {triangles:b.renderer.info.render.triangles,calls:b.renderer.info.render.calls,textures:b.renderer.info.memory.textures};
    };
    const render=drawColony();let modelMeshes=0,textured=0,normalMapped=0,glass=0;
    b.colony.group.traverse(o=>{if(o.isMesh){modelMeshes++;if(o.material.map)textured++;if(o.material.normalMap)normalMapped++;if(o.material.name==='Conservatory_glass')glass++;}});
    return {version:document.getElementById('version').textContent,state:b.colony.assetState,apiState:BeltRunnerGardenColony.state,active:BeltRunnerGardenColony.active,modelMeshes,textured,normalMapped,glass,render,traffic:b.traffic.length,pads:b.padSlots.length,planet:b.planets[0].name};
  });
  assert.equal(setup.state,mode==='missing'?'fallback':'ready');assert.equal(setup.active,1);assert.equal(setup.planet,'Meridian');assert.ok(setup.traffic>0);assert.ok(setup.pads>0);
  if(mode!=='missing'){assert.equal(setup.modelMeshes,23);assert.ok(setup.textured>=4);assert.ok(setup.normalMapped>=3);assert.equal(setup.glass,1);}
  await page.screenshot({path:path.join(out,'previews',mode+'-overview.png')});
  const checks=[];
  if(mode==='http'){
    for(const view of ['gardens','berths']){await page.evaluate(view=>drawColony(view),view);await page.screenshot({path:path.join(out,'previews',view+'.png')});}
    checks.push(await page.evaluate(()=>{
      const b=BeltRunner,c=b.colony,T=THREE;c.group.updateMatrixWorld(true);
      // Raycasts verify the actual exported surfaces at every AI landing-pad center.
      const ray=new T.Raycaster(),meshes=[];c.group.traverse(o=>{if(o.isMesh&&!o.material.transparent)meshes.push(o);});
      const glass=c.model.getObjectByName('Habitat_Rings_Conservatory_glass'),positions=glass.geometry.attributes.position,point=new T.Vector3();let outerRoof=0,innerRoof=0;
      for(let i=0;i<positions.count;i++){point.fromBufferAttribute(positions,i).applyMatrix4(glass.matrixWorld);const r=Math.hypot(point.x,point.z),outer=r>41000,extent=Math.hypot(r-(outer?52000:30000),point.y);if(outer)outerRoof=Math.max(outerRoof,extent);else innerRoof=Math.max(innerRoof,extent);}
      if(outerRoof>3400||innerRoof>2100)throw Error('Conservatory glass extends outside the ring collider');
      const pads=b.padSlots.filter(s=>s.type==='pad'),gaps=[];
      for(const s of pads){ray.set(s.pos.clone().add(new T.Vector3(0,s.side*500,0)),new T.Vector3(0,-s.side,0));ray.far=1200;const hits=ray.intersectObjects(meshes,false);if(!hits.length)throw Error('Landing pad has no rendered surface');const gap=hits[0].point.distanceTo(s.pos);if(gap>80)throw Error('Landing pad shifted by '+gap);gaps.push(gap);}
      // Holding point and the unchanged ring physics still protect the carrier.
      const start=b.ship.pos.clone();b.setTestDocked(false);b.ship.pos.copy(b.HOLD.park);b.colonyCollide();if(b.ship.pos.distanceTo(b.HOLD.park)>1)throw Error('Holding station collides with new colony');
      b.ship.pos.set(52000,0,0);b.ship.vel.set(0,0,0);b.colonyCollide();if(b.ship.pos.distanceTo(new T.Vector3(52000,0,0))<1)throw Error('Original ring collider no longer protects habitat');b.ship.pos.copy(start);
      const before=c.ring.rotation.y;b.updateVisuals(.1,12);if(c.ring.rotation.y===before)throw Error('Habitat does not rotate');
      return {landingPads:pads.length,maxLandingSurfaceGap:Math.max(...gaps),outerRoofExtent:outerRoof,innerRoofExtent:innerRoof,holdingClear:true,ringCollision:true,ringAnimation:true};
    }));
    checks.push(await page.evaluate(async()=>{
      const b=BeltRunner,home=b.ZONES.find(z=>z.hub),belt=b.ZONES.find(z=>z.id==='kessler');
      const original=b.colony.model.getObjectByName('Habitat_Rings_Ivory_ceramic_alloy'),geometry=original.geometry,map=original.material.map;let disposed=0;geometry.addEventListener('dispose',()=>disposed++);map.addEventListener('dispose',()=>disposed++);
      const counts=[];
      for(let i=0;i<3;i++){
        const old=b.colony;b.loadZone(belt);if(!old.removed||BeltRunnerGardenColony.active!==0||old.group.children.length)throw Error('Colony remains after leaving Hub');
        b.loadZone(home);await Promise.all([b.colony.assetReady,b.planets[0].assetReady]);
        const current=b.colony.model.getObjectByName('Habitat_Rings_Ivory_ceramic_alloy');if(current.geometry!==geometry||current.material.map!==map||disposed)throw Error('Shared colony resources discarded');counts.push(drawColony().textures);
      }
      if(new Set(counts).size!==1)throw Error('Texture count grows on Hub visits');
      b.loadZone(home);const removed=b.colony;b.loadZone(belt);await removed.assetReady;if(removed.group.children.length||BeltRunnerGardenColony.active!==0)throw Error('Late asset attached after leaving zone');
      return {repeatedVisits:3,textureCounts:counts,sharedGeometry:true,sharedTextures:true,lateLoadSafe:true};
    }));
    // Standalone viewer uses the same loader / materials and real Meridian backdrop.
    await page.goto(base+'/assets/colony_garden/preview.html?debug',{waitUntil:'load'});
    await page.waitForFunction(()=>window.GardenPreview?.c.assetState==='ready'&&GardenPreview.p.assetState==='ready',null,{timeout:90000,polling:100});
    for(const view of ['overview','gardens','berths']){
      await page.evaluate(view=>{GardenPreview.setSpin(false);GardenPreview.view(view);GardenPreview.draw(0);},view);
      await page.screenshot({path:path.join(out,'previews','viewer-'+view+'.png')});
    }
    await page.getByRole('button',{name:'Resume rotation'}).click();
    const rotated=await page.evaluate(()=>{const x=GardenPreview.c.ring.rotation.y;GardenPreview.draw(1);return GardenPreview.c.ring.rotation.y>x;});assert.ok(rotated);checks.push({viewerControls:true});
  }
  assert.deepEqual(errors,[]);assert.equal(sha(fs.readFileSync(file)),sha(source),'Shared game changed while testing');
  const result={passed:true,mode,gameSHA256:sha(source),assetSHA256:sha(fs.readFileSync(path.join(out,'garden-habitat.glb'))),loaderSHA256:sha(fs.readFileSync(path.join(out,'load-colony.js'))),setup,checks,errors};fs.writeFileSync(path.join(out,mode+'-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}finally{if(browser)await browser.close();server.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
