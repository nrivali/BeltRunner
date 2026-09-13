// Validate the Hub homeworld in the real game: node tests/hub-planet-integration.cjs [http|file|script|missing]
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'assets/hub_planet'),mode=process.argv[2]||'http';
const file=path.join(root,'belt-runner-3d.html'),source=fs.readFileSync(file,'utf8'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const instrumentation='Object.assign(window.BeltRunner,{HOLD,COLONY_SITES,holdAtColony,setTestDocked:value=>{docked=value;},rockCollisionGrid,';
const server=http.createServer((req,res)=>{
  const url=new URL(req.url,'http://localhost'),p=path.resolve(root,'.'+decodeURIComponent(url.pathname));
  if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  if(p===file){res.setHeader('Content-Type','text/html; charset=utf-8');res.end(source.replace('Object.assign(window.BeltRunner,{rockCollisionGrid,',instrumentation));return;}
  fs.readFile(p,(e,b)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.png')?'image/png':p.endsWith('.jpg')?'image/jpeg':'application/octet-stream');res.end(b);});
});
(async()=>{let browser;try{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/Shader|WebGLProgram/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;let s=8192;Math.random=()=>{s=(1664525*s+1013904223)>>>0;return s/4294967296;};});
  if(mode==='script'||mode==='missing')await page.route('**/hub_planet/homeworld.glb',r=>r.fulfill({status:404,body:'missing'}));
  if(mode==='missing')await page.route('**/hub_planet/homeworld.data.js',r=>r.fulfill({status:404,body:'missing'}));
  const url=mode==='file'?require('node:url').pathToFileURL(file).href:`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
  await page.goto(url+'?debug',{waitUntil:'load',timeout:60000});
  await page.waitForFunction(()=>window.BeltRunner?.rockAssets.ready&&BeltRunner.carrierAsset.state==='ready'&&BeltRunner.playerAsset.state==='ready',null,{timeout:60000,polling:100});
  const setup=await page.evaluate(async()=>{
    const b=BeltRunner,z=b.ZONES.find(z=>z.hub);b.loadZone(z);await b.planets[0].assetReady;
    const p=b.planets[0],surface=p.group.getObjectByName('homeworld_surface'),cloud=p.group.getObjectByName('homeworld_clouds');
    window.drawHomeworld=(view='colony')=>{
      [...document.querySelectorAll('body > :not(canvas):not(script)')].forEach(e=>e.style.display='none');
      const p=b.planets[0],sun=new THREE.Vector3(...b.zone.sunDir).normalize();
      if(view==='colony'){
        b.camera.position.set(-90000,65000,145000);b.camera.lookAt(new THREE.Vector3(20000,-55000,-50000));
      }else if(view==='arrival'){
        b.camera.position.set(-52000,21000,73000);b.camera.lookAt(new THREE.Vector3(0,-42000,-45000));
      }else{
        const dir=view==='night'?sun.clone().negate():sun.clone().add(new THREE.Vector3(.15,.08,.30)).normalize();
        b.camera.position.copy(p.pos).addScaledVector(dir,p.r*3.15);b.camera.lookAt(p.pos);
      }
      b.camera.updateMatrixWorld(true);
      b.lighting.update({camera:b.camera,quality:'balanced',station:b.station,asteroids:b.asteroids,scenery:b.scenery,rockAssets:b.rockAssets,dt:.2});
      b.rockAssets.render(b.camera,'balanced');b.renderer.render(b.scene,b.camera);
      return {sunVisible:b.lighting.status.sunVisible,textures:b.renderer.info.memory.textures,triangles:b.renderer.info.render.triangles};
    };
    const first=window.drawHomeworld();
    return {version:document.getElementById('version').textContent,zone:b.zone.id,state:p.assetState,homeworld:p.homeworld,radius:p.r,position:p.pos.toArray(),oreRocks:b.asteroids.length,albedo:surface?.material.map.image.width,normal:!!surface?.material.normalMap,cities:!!surface?.material.emissiveMap,clouds:cloud?.material.map.image.width,first};
  });
  assert.equal(setup.zone,'hub');assert.equal(setup.homeworld,true);assert.equal(setup.state,mode==='missing'?'fallback':'ready');assert.equal(setup.oreRocks,0);assert.deepEqual(setup.position,[150000,-430000,-360000]);
  if(mode!=='missing'){assert.equal(setup.albedo,4096);assert.equal(setup.clouds,4096);assert(setup.normal&&setup.cities);}
  await page.screenshot({path:path.join(out,'previews',mode==='http'?'hub-colony.png':mode+'.png')});
  const checks=[];
  if(mode==='http'){
    for(const view of ['arrival','day','night']){const render=await page.evaluate(v=>drawHomeworld(v),view);checks.push({view,...render});await page.screenshot({path:path.join(out,'previews',view+'.png')});}
    const holding=await page.evaluate(()=>{
      const b=BeltRunner;b.holdAtColony();b.updateVisuals(.016,1);
      b.lighting.update({camera:b.camera,quality:'balanced',station:b.station,asteroids:b.asteroids,scenery:b.scenery,rockAssets:b.rockAssets,dt:.2});b.rockAssets.render(b.camera,'balanced');b.renderer.render(b.scene,b.camera);
      const globe=b.planets[0].pos.clone().project(b.camera),colony=b.colony.pos.clone().project(b.camera);
      if(Math.abs(globe.x)>1.15||globe.y< -1.15||Math.abs(colony.x)>1.1||Math.abs(colony.y)>1.1)throw Error('Holding camera does not frame the homeworld and colony');
      return {holdingCamera:true,planetScreen:globe.toArray(),colonyScreen:colony.toArray()};
    });checks.push(holding);await page.screenshot({path:path.join(out,'previews/holding-station.png')});
    checks.push(await page.evaluate(()=>{
      const b=BeltRunner,p=b.planets[0],V=THREE.Vector3;
      const stationClearance=Math.min(...b.COLONY_SITES.map(s=>s.pos.distanceTo(p.pos)-p.r-54000*s.scale));
      if(stationClearance<30000)throw Error('Planet intersects colony approaches');
      if(p.pos.y+p.r*1.018>=-100000)throw Error('Planet reaches the traffic altitude envelope');
      const angle=p.clouds.rotation.y;BeltRunnerHomeworld.update(p,10);if(p.clouds.rotation.y===angle)throw Error('Clouds are static');
      const sun=new V(...b.zone.sunDir).normalize();b.camera.position.copy(p.pos).addScaledVector(sun,-p.r*2);
      b.lighting.update({camera:b.camera,station:b.station,asteroids:[],scenery:[],dt:.2});if(b.lighting.status.sunVisible!==0)throw Error('Offset planet fails to eclipse sun');
      b.camera.position.copy(p.pos).addScaledVector(sun,p.r*2);b.lighting.update({camera:b.camera,station:b.station,asteroids:[],scenery:[],dt:.2});if(b.lighting.status.sunVisible!==1)throw Error('Day side sun occluded');
      b.setTestDocked(false);b.ship.pos.copy(p.pos).add(new V(0,p.r,0));b.ship.vel.set(0,0,0);b.update(.001);
      if(b.ship.pos.distanceTo(p.pos)<p.r*1.006)throw Error('Carrier crossed offset planet collider');
      return {stationClearance,trafficEnvelopeClear:true,cloudsAnimate:true,offsetEclipse:true,offsetCollider:true};
    }));
    checks.push(await page.evaluate(async()=>{
      const b=BeltRunner,home=b.ZONES.find(z=>z.hub),belt=b.ZONES.find(z=>z.id==='kessler'),initial=b.planets[0].group.getObjectByName('homeworld_surface'),geometry=initial.geometry,map=initial.material.map;
      let geometryDisposed=0,mapDisposed=0;geometry.addEventListener('dispose',()=>geometryDisposed++);map.addEventListener('dispose',()=>mapDisposed++);
      const textureCounts=[];
      for(let i=0;i<3;i++){
        const old=b.planets[0];b.loadZone(belt);await b.planets[0].assetReady;
        if(!old.removed||BeltRunnerHomeworld.active!==0||b.planets[0].name!=='Ferron')throw Error('Homeworld leaked into belt');
        b.ship.pos.set(...home.planet.position);b.loadZone(home);await b.planets[0].assetReady;
        if(b.ship.pos.distanceTo(b.HOLD.park)>1)throw Error('Old Hub save not moved out of planet');
        textureCounts.push(drawHomeworld('day').textures);
      }
      const last=b.planets[0].group.getObjectByName('homeworld_surface');
      if(last.geometry!==geometry||last.material.map!==map||geometryDisposed||mapDisposed||BeltRunnerHomeworld.active!==1)throw Error('Shared homeworld cache disposed or duplicated');
      if(new Set(textureCounts).size!==1)throw Error('Texture count grows across visits');
      return {repeatedVisits:3,textureCounts,sharedGeometry:true,sharedTextures:true,oldSaveSafe:true};
    }));
    const race=await page.evaluate(async()=>{const b=BeltRunner;b.loadZone(b.ZONES.find(z=>z.hub));const old=b.planets[0];b.loadZone(b.ZONES.find(z=>z.id==='kessler'));await old.assetReady;return {removed:old.removed,children:old.group.children.length,active:BeltRunnerHomeworld.active};});
    assert.deepEqual(race,{removed:true,children:0,active:0});checks.push({race});
  }
  assert.deepEqual(errors,[]);assert.equal(sha(fs.readFileSync(file)),sha(source),'Shared game changed during verification');
  const result={passed:true,mode,gameSHA256:sha(source),setup,checks,errors};fs.writeFileSync(path.join(out,mode+'-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}finally{if(browser)await browser.close();server.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
