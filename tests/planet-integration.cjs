/* Verify real scene rendering, all zones, asset fallbacks and shared-resource lifetime. */
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'assets/planet_v2'),mode=process.argv[2]||'http';
const hash=()=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'belt-runner-3d.html'))).digest('hex');
const server=http.createServer((req,res)=>{
  const url=new URL(req.url,'http://localhost');
  if(!/^\/(belt-runner-3d\.html|assets\/|vendor\/|sfx\/)/.test(url.pathname)){res.writeHead(404).end();return;}
  const p=path.resolve(root,'.'+decodeURIComponent(url.pathname));
  if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  fs.readFile(p,(e,data)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',p.endsWith('.html')?'text/html; charset=utf-8':p.endsWith('.js')?'text/javascript':p.endsWith('.png')?'image/png':p.endsWith('.jpg')?'image/jpeg':'application/octet-stream');res.end(data);});
});
(async()=>{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],initialSHA=hash();
    const assetSHA256=crypto.createHash('sha256').update(fs.readFileSync(path.join(out,'planet.glb'))).digest('hex');
    page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/Shader|WebGLProgram/.test(m.text()))errors.push(m.text());});
    await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;let s=28761;Math.random=()=>{s=(1664525*s+1013904223)>>>0;return s/4294967296;};});
    if(mode==='script'||mode==='missing')await page.route('**/assets/planet_v2/planet.glb',r=>r.fulfill({status:404,body:'missing'}));
    if(mode==='invalid')await page.route('**/assets/planet_v2/planet.glb',r=>r.fulfill({status:200,body:'invalid glb'}));
    if(mode==='missing')await page.route('**/assets/planet_v2/planet.data.js',r=>r.fulfill({status:404,body:'missing'}));
    const url=mode==='file'?require('node:url').pathToFileURL(path.join(root,'belt-runner-3d.html')).href:`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
    await page.goto(url+'?debug',{waitUntil:'load',timeout:60000});
    await page.waitForFunction(()=>window.BeltRunner?.rockAssets.ready&&BeltRunner.carrierAsset.state==='ready'&&BeltRunner.playerAsset.state==='ready',null,{polling:100,timeout:60000});
    if(mode!=='baseline')await page.waitForFunction(()=>['ready','fallback'].includes(BeltRunner.planets[0]?.assetState),null,{polling:100,timeout:60000});
    const setup=await page.evaluate(()=>{
      const b=BeltRunner,V=THREE.Vector3;
      [...document.querySelectorAll('body > :not(canvas):not(script)')].forEach(e=>e.style.display='none');
      b.state.tut=-1;b.startGame();
      window.drawPlanet=(phase='orbit')=>{
        const p=b.planets[0],sun=new V(...b.zone.sunDir).normalize(),right=new V().crossVectors(sun,new V(0,1,0)).normalize();
        if(phase==='night')b.camera.position.copy(sun).multiplyScalar(-p.r*3);
        else if(phase==='surface')b.camera.position.copy(sun).multiplyScalar(p.r*1.07).addScaledVector(right,p.r*.55);
        else b.camera.position.copy(sun).multiplyScalar(p.r*2.4).addScaledVector(right,p.r*1.75).add(new V(0,p.r*.42,0));
        b.camera.lookAt(p.pos);b.camera.updateMatrixWorld(true);
        b.lighting.update({camera:b.camera,station:b.station,asteroids:b.asteroids,scenery:b.scenery,rockAssets:b.rockAssets,dt:.2});
        b.rockAssets.render(b.camera,'balanced');b.renderer.render(b.scene,b.camera);
      };
      drawPlanet();return {version:document.getElementById('version').textContent,asset:b.planets[0].assetState||'procedural',radius:b.planets[0].r};
    });
    await page.screenshot({path:path.join(out,'previews',mode==='baseline'?'before.png':mode==='http'?'ferron-orbit.png':mode+'.png')});
    if(mode==='baseline'){console.log(JSON.stringify({mode,setup,errors}));return;}
    assert.equal(setup.asset,mode==='missing'?'fallback':'ready');
    const checks=[];
    if(mode==='http'){
      await page.evaluate(()=>drawPlanet('surface'));await page.screenshot({path:path.join(out,'previews/ferron-surface.png')});
      const brightness=await page.evaluate(()=>{
        const b=BeltRunner,gl=b.renderer.getContext();
        const sample=()=>{const px=new Uint8Array(4);gl.readPixels(gl.drawingBufferWidth>>1,gl.drawingBufferHeight>>1,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);return (px[0]+px[1]+px[2])/3;};
        drawPlanet();const day=sample();drawPlanet('night');return {day,night:sample(),sunVisible:b.lighting.status.sunVisible};
      });
      await page.screenshot({path:path.join(out,'previews/ferron-night.png')});
      assert(brightness.day>brightness.night*2,JSON.stringify(brightness));assert.equal(brightness.sunVisible,0);checks.push({brightness});
      const activeZones=await page.evaluate(()=>BeltRunner.ZONES.map(z=>z.id).filter(id=>!['hub','kessler'].includes(id)).concat(['hub','kessler']));
      for(const id of activeZones){
        const result=await page.evaluate(async id=>{
          const b=BeltRunner,old=b.planets[0],z=b.ZONES.find(z=>z.id===id);b.loadZone(z);
          if(z.hub)return {zone:id,planetCount:b.planets.length,active:BeltRunnerPlanets.active,oldRemoved:old.removed};
          await b.planets[0].assetReady;drawPlanet();const p=b.planets[0],s=p.group.getObjectByName('planet_surface');
          return {zone:id,state:p.assetState,r:p.r,collider:p.r*1.006,normal:!!s.material.normalMap,albedo:s.material.map.image.width,roughness:!!s.material.roughnessMap,active:BeltRunnerPlanets.active,oldRemoved:old?.removed,castShadow:s.castShadow,textures:b.renderer.info.memory.textures,geometry:s.geometry.uuid};
        },id);
        if(id==='hub'){assert.equal(result.active,0);assert.equal(result.planetCount,0);}else{assert.equal(result.state,'ready');assert.equal(result.normal,true);assert.equal(result.albedo,4096);assert.equal(result.active,1);assert.equal(result.castShadow,false);}
        checks.push(result);
        if(id!=='hub')await page.screenshot({path:path.join(out,'previews',id+'.png')});
      }
      const lifetime=await page.evaluate(async()=>{
        const b=BeltRunner,first=b.planets[0].group.getObjectByName('planet_surface'),geo=first.geometry,map=first.material.map;
        let geoDisposed=0,mapDisposed=0,matDisposed=0;
        geo.addEventListener('dispose',()=>geoDisposed++);map.addEventListener('dispose',()=>mapDisposed++);first.material.addEventListener('dispose',()=>matDisposed++);
        for(let i=0;i<6;i++){b.loadZone(b.ZONES.find(z=>z.hub));b.loadZone(b.ZONES.find(z=>z.id==='kessler'));await b.planets[0].assetReady;}
        drawPlanet();return {geoDisposed,mapDisposed,matDisposed,active:BeltRunnerPlanets.active,sameGeometry:geo===b.planets[0].group.getObjectByName('planet_surface').geometry,radiusMax:BeltRunnerPlanets.radiusMax};
      });
      assert.deepEqual({geo:lifetime.geoDisposed,map:lifetime.mapDisposed,mat:lifetime.matDisposed,active:lifetime.active,same:lifetime.sameGeometry},{geo:0,map:0,mat:1,active:1,same:true});assert(lifetime.radiusMax<1.006);checks.push({lifetime});
      // Warp twice while the shared promise resolves: removed planets must not reappear.
      const race=await page.evaluate(async()=>{const b=BeltRunner;b.loadZone(b.ZONES.find(z=>z.id==='kessler'));const old=b.planets[0];b.loadZone(b.ZONES.find(z=>z.hub));await old.assetReady;return {removed:old.removed,children:old.group.children.length,active:BeltRunnerPlanets.active};});
      assert.deepEqual(race,{removed:true,children:0,active:0});checks.push({race});
    }
    assert.deepEqual(errors,[],errors.join('\n'));assert.equal(hash(),initialSHA,'Game changed during verification');
    const result={passed:true,mode,gameSHA256:initialSHA,assetSHA256,setup,checks,errors};
    fs.writeFileSync(path.join(out,mode+'-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
  }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
