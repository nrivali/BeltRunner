const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'assets/asteroids_v2');
const expectedVersion='v'+fs.readFileSync(path.join(root,'belt-runner-3d.html'),'utf8').match(/const GAME_VERSION = '([^']+)'/)[1];
const server=http.createServer((req,res)=>{const p=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}fs.readFile(p,(e,b)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':'application/octet-stream');res.end(b);});});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const results=[];
 try{
  const helperCheck=process.argv.includes('--helper-missing');
  for(const mode of (helperCheck?['collision-missing']:process.argv.includes('--smoke')?['http']:['http','file','script-fallback','missing','invalid'])){
   const page=await browser.newPage({viewport:{width:1440,height:960}}),errors=[];
   page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/WebGLProgram|Shader Error/.test(m.text()))errors.push(m.text());});
   await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;});
   await page.route(/^https:\/\//,r=>r.abort());
   if(mode==='collision-missing')await page.route('**/mesh-collision.js',r=>r.fulfill({status:200,contentType:'text/javascript',body:''}));
   if(mode==='missing'||mode==='script-fallback')await page.route('**/asteroids-game.bin.gz',r=>r.fulfill({status:404,body:'missing'}));
   if(mode==='missing')await page.route('**/asteroids-game.data.js',r=>r.fulfill({status:404,body:'missing'}));
   if(mode==='invalid')await page.route('**/asteroids-game.bin.gz',r=>r.fulfill({status:200,body:'invalid'}));
   const url=mode==='file'?pathToFileURL(path.join(root,'belt-runner-3d.html')).href:`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
   await page.goto(url+'?debug',{waitUntil:'load',timeout:60000});
   await page.waitForFunction(()=>window.BeltRunner?.rockAssets.status.state!=='loading'&&window.BeltRunner?.rockAssets.status.state,null,{timeout:60000,polling:100});
   const result=await page.evaluate(()=>{const b=BeltRunner;return {status:{...b.rockAssets.status},count:b.asteroids.length,attached:b.asteroids.filter(a=>a.asset).length,scenery:b.scenery.filter(a=>a.asset).length,version:document.getElementById('version').textContent};});
   const fallback=mode==='missing'||mode==='invalid'||mode==='collision-missing';assert.equal(result.status.state,fallback?'fallback':'ready');assert.equal(result.version,expectedVersion);
   if(fallback){
    await page.waitForFunction(()=>window.BeltRunnerRockSurface.status.state!=='loading',null,{polling:100});
    assert.equal(result.attached,0);assert.ok(await page.evaluate(()=>BeltRunner.asteroids.every(a=>a.bodyGeo&&a.group.children.length)));
   }else{
    assert.equal(result.attached,result.count);assert.ok(result.scenery>0);assert.equal(result.status.models,84);assert.equal(result.status.source,mode==='file'||mode==='script-fallback'?'script':'binary');
    result.render=await page.evaluate(()=>{const b=BeltRunner;b.rockAssets.render(b.camera,'balanced');b.renderer.render(b.scene,b.camera);return {...b.rockAssets.status,totalCalls:b.renderer.info.render.calls,totalTriangles:b.renderer.info.render.triangles};});
    if(mode==='http'){
     result.physics=await page.evaluate(()=>{
      const b=BeltRunner,api=b.rockAssets,V=THREE.Vector3;
      const fixture=(shape,variant,r=600)=>{const group=new THREE.Group(),seed=variant==='A'?2:1;const a={shape,seed,baseR:r,r,group,pos:group.position,ore:'iron',barren:false,dead:false,hp:100,hpMax:100,amount:10,max:10};api.register(a);if(a.asset.variant!==variant)throw Error('Variant mismatch');return a;};
      const arch=fixture('hollow','B'),cave=fixture('hollow','A'),lump=fixture('lumpy','A');
      if(api.rayHit(arch,new V(0,-1800,0),new V(0,1,0),3600))throw Error('Arch obstructed');
      if(b.rockInside(arch,new V())||b.rockInside(cave,new V(0,-240,0)))throw Error('Cavity considered solid');
      let passageSteps=0;for(let y=-1800;y<=1800;y+=45){if(api.contact(arch,new V(0,y,0),b.SHIP_R))throw Error('Ship cannot pass arch at '+y);passageSteps++;}
      const origin=new V(1800,100,0),sample=api.surfaceSample(lump,origin),outside=sample.point.clone().addScaledVector(sample.normal,24);b.ship.vel.set(0,0,0);b.ship.pos.copy(outside);
      if(!b.noisyCollide(lump,outside)||b.rockInside(lump,b.ship.pos))throw Error('Ship surface collision failed');
      const nearest=api.surfaceSample(lump,b.ship.pos);if(b.ship.pos.distanceTo(nearest.point)<b.SHIP_R-2)throw Error('Ship hull still intersects rock');
      const aim=api.aimPoint(arch,new V(0,-1800,0));if(!api.rayHit(arch,new V(0,-1800,0),aim.clone().sub(new V(0,-1800,0)).normalize(),4000))throw Error('Auto aim misses arch wall');
      api.setHeat(lump,.7);b.addBurn(lump,sample.point,18);if(!lump.burnMesh||lump.asset.heat!==.7)throw Error('Heat or scorch missing');
      const small=fixture('hollow','B',100),old=b.asteroids.map(a=>a.dead);b.asteroids.forEach(a=>a.dead=true);b.asteroids.push(small);
      const direction=new V(0,1,0);b.ship.q.setFromUnitVectors(new V(0,0,1),direction);b.ship.pos.copy(new V(0,-250,0).sub(new V(0,-7.8,57).applyQuaternion(b.ship.q)));
      if(b.findTarget()?.obj===small)throw Error('Laser targets empty arch opening');
      b.asteroids.pop();b.asteroids.forEach((a,i)=>a.dead=old[i]);
      return {passageSteps,shipCollision:true,scorch:true,heat:true,manualRayThroughArch:true,autoAimHitsWall:true};
     });
     result.breaking=await page.evaluate(()=>{
      const b=BeltRunner,a=b.asteroids.find(a=>a.cls==='large'&&!a.barren),before=b.asteroids.length,geometryCount=b.rockAssets.templates.size;
      a.inScene=true;b.scene.add(a.group);const ore=a.ore;b.breakRock(a,false);
      const fragments=b.asteroids.slice(before);if(!a.dead||fragments.length<3||fragments.some(f=>!f.asset||f.ore!==ore||!f.fragment))throw Error('Fragment integration failed');
      if(!b.debris.length||!b.debris.every(d=>d.mesh.material.map&&d.mesh.material.normalMap))throw Error('Scrap texture missing');
      if(b.rockAssets.templates.size!==geometryCount)throw Error('Shared meshes were disposed');
      return {fragments:fragments.length,drops:b.drops.length,scrap:b.debris.length,sharedModels:geometryCount};
     });
     result.field=await page.evaluate(()=>{
      const b=BeltRunner,api=b.rockAssets,V=THREE.Vector3,origin=new V(500000,100000,500000),shapes=[...new Set([...api.templates.values()].map(t=>t.key.split('_')[0]))];
      b.asteroids.forEach(a=>a.dead=true);b.scenery.forEach(a=>a.dead=true);
      for(let i=0;i<1000;i++){
       const group=new THREE.Group();group.position.copy(origin).add(new V((i%25-12)*100,(Math.floor(i/25)%10-4.5)*105,1000+Math.floor(i/250)*500));group.rotation.set(i*.31,i*.57,i*.11);
       const a={shape:shapes[i%shapes.length],seed:i+.1,baseR:30,r:30,group,pos:group.position,ore:['iron','copper','gold','platinum','crystal'][i%5],barren:i%6===0,dead:false};api.register(a);b.asteroids.push(a);
      }
      b.camera.position.copy(origin);b.camera.lookAt(origin.clone().add(new V(0,0,1600)));b.camera.updateMatrixWorld(true);api.render(b.camera,'balanced');
      window.assetTestVisibility=b.scene.children.map(child=>[child,child.visible]);
      for(const child of b.scene.children){if(!child.isLight&&!child.name.startsWith('asteroid_batch_'))child.visible=false;}
      b.renderer.render(b.scene,b.camera);const near={...api.status,totalCalls:b.renderer.info.render.calls,totalTriangles:b.renderer.info.render.triangles};
      if(near.visible<400||near.drawCalls>84||near.drawCalls>=near.visible/3)throw Error('Instancing ineffective');
      b.camera.position.z-=20000;b.camera.lookAt(origin.clone().add(new V(0,0,1600)));b.camera.updateMatrixWorld(true);api.render(b.camera,'balanced');const distant={...api.status};
      if(distant.lodCounts[0]!==0)throw Error('Near geometry used at distance');
      b.camera.position.copy(origin);b.camera.lookAt(origin.clone().add(new V(0,0,1600)));b.camera.updateMatrixWorld(true);api.render(b.camera,'balanced');b.renderer.render(b.scene,b.camera);
      window.assetTestUI=[...document.querySelectorAll('body > :not(canvas):not(script)')].map(e=>[e,e.style.display]);window.assetTestUI.forEach(([e])=>e.style.display='none');return {near,distant};
     });
     await page.screenshot({path:path.join(out,'previews/integrated-field.tmp.png')});fs.renameSync(path.join(out,'previews/integrated-field.tmp.png'),path.join(out,'previews/integrated-field.png'));
     result.zones=await page.evaluate(()=>{const b=BeltRunner,names=[];window.assetTestVisibility.forEach(([e,v])=>e.visible=v);window.assetTestUI.forEach(([e,v])=>e.style.display=v);for(const key of ['frost','hub','kessler']){const z=b.ZONES.find(z=>z.id===key);if(!z)throw Error('Missing test zone');b.loadZone(z);b.rockAssets.render(b.camera,'balanced');if(b.asteroids.some(a=>!a.asset)||b.scenery.some(a=>!a.asset))throw Error('Warp left old rocks');names.push({zone:key,rocks:b.asteroids.length,scenery:b.scenery.length});}return names;});
     result.play=await page.evaluate(()=>{
      const b=BeltRunner,V=THREE.Vector3;b.state.tut=-1;b.startGame();b.startDeparture();let steps=0;while(b.cut&&steps++<400)b.update(.05);if(b.cut||b.flags.docked)throw Error('Departure failed');
      const a=b.asteroids.find(a=>a.ore==='gold'&&a.cls==='large'&&a.shape!=='hollow');if(!a)throw Error('No review rock');b.ship.pos.copy(a.pos).add(new V(0,a.baseR*.2,-a.boundR*3.6));b.ship.vel.set(0,0,0);b.ship.q.identity();
      const start=performance.now();for(let i=0;i<30;i++)b.update(.016);const updateMs=(performance.now()-start)/30;
      b.updateVisuals(.016,5);const lightDirection=new V(...b.zone.sunDir).normalize();b.camera.position.copy(a.pos).addScaledVector(lightDirection,a.boundR*4.5);b.camera.lookAt(a.pos);b.camera.updateMatrixWorld(true);b.rockAssets.render(b.camera,'balanced');b.renderer.render(b.scene,b.camera);
      return {departureSteps:steps,simulationMsPerFrame:updateMs,visibleRocks:b.rockAssets.status.visible,rockDrawCalls:b.rockAssets.status.drawCalls};
     });
     await page.screenshot({path:path.join(out,'previews/in-game.tmp.png')});fs.renameSync(path.join(out,'previews/in-game.tmp.png'),path.join(out,'previews/in-game.png'));
     result.mining=await page.evaluate(()=>{
      const b=BeltRunner,V=THREE.Vector3,position=b.ship.pos.clone().add(new V(0,0,3000));
      const a=b.makeAsteroid(b.asteroids[0].belt,null,null,{cls:'small',r:100,ore:'iron',barren:false,pos:position,amount:80});a.hp=a.hpMax=100000;a.free=true;a.vel=new V();b.asteroids.push(a);b.ship.q.identity();const offset=new V(0,0,-a.boundR-150),hp=a.hp;
      b.keys[' ']=true;
      for(let i=0;i<140;i++){b.ship.pos.copy(a.pos).add(offset);b.ship.vel.set(0,0,0);b.update(.05);b.updateVisuals(.05,8+i*.05);}
      b.keys[' ']=false;
      if(a.hp>=hp||b.heatFx.rock!==a||!a.asset.heat)throw Error('Live mining did not heat and damage the new rock');
      const error=b.rockAssets.surfaceSample(a,b.heatFx.pos).point.distanceTo(b.heatFx.pos);if(error>2)throw Error('Mining heat detached from visible surface');
      return {damage:hp-a.hp,heat:b.heatFx.heat,bodyHeat:a.asset.heat,surfaceError:error};
     });
    }
   }
   assert.deepEqual(errors,[],errors.join('\n').slice(0,4000));result.errors=errors;results.push({mode,...result});console.log(mode,JSON.stringify({state:result.status.state,rocks:result.count,render:result.render?.drawCalls,field:result.field?.near?.drawCalls}));await page.close();
  }
  fs.writeFileSync(path.join(out,helperCheck?'collision-fallback-validation.json':'integration-validation.json'),JSON.stringify({passed:true,results},null,2)+'\n');
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
