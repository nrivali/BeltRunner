const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'assets/lighting');
fs.mkdirSync(path.join(out,'previews'),{recursive:true});
let servedGameSHA=null;
const server=http.createServer((req,res)=>{
 const url=new URL(req.url,'http://localhost'),p=path.resolve(root,'.'+decodeURIComponent(url.pathname));
 if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}
 fs.readFile(p,(error,data)=>{
  if(error){res.writeHead(404).end();return;}
  if(url.pathname==='/belt-runner-3d.html')servedGameSHA=require('node:crypto').createHash('sha256').update(data).digest('hex');
  res.setHeader('Content-Type',p.endsWith('.html')?'text/html':p.endsWith('.js')?'text/javascript':'application/octet-stream');res.end(data);
 });
});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:960}}),errors=[];
  page.on('pageerror',e=>{errors.push(e.message);console.error(e.message);});page.on('console',m=>{if(m.type()==='error'&&/Shader|WebGLProgram/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;let seed=28761;Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};});
  const directFile=process.argv.includes('--file');
  const gameURL=directFile?require('node:url').pathToFileURL(path.join(root,'belt-runner-3d.html')).href:`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
  const beforeLoad=fs.readFileSync(path.join(root,'belt-runner-3d.html'));
  await page.goto(gameURL+'?debug',{waitUntil:'load',timeout:60000});
  // Hash the actual served bytes; DevTools response.body() may transcode HTML
  // from its inferred charset, which would not be a hash of the source file.
  const loadedSHA=directFile?require('node:crypto').createHash('sha256').update(beforeLoad).digest('hex'):servedGameSHA;
  await page.waitForFunction(()=>window.BeltRunner?.rockAssets.ready&&BeltRunner.carrierAsset.state==='ready'&&BeltRunner.playerAsset.state==='ready',null,{polling:100,timeout:60000});
  const setup=await page.evaluate(()=>{
   const b=BeltRunner,V=THREE.Vector3;
   [...document.querySelectorAll('body > :not(canvas):not(script)')].forEach(e=>e.style.display='none');
   window.drawLighting=()=>{b.lighting.update({camera:b.camera,station:b.station,asteroids:b.asteroids,scenery:b.scenery,rockAssets:b.rockAssets,quality:window.testQuality||'balanced',dt:.12});b.rockAssets.render(b.camera,window.testQuality||'balanced');b.renderer.render(b.scene,b.camera);};
   b.state.tut=-1;b.startGame();b.startDeparture();for(let i=0;i<180&&b.cut;i++)b.update(.05);b.updateVisuals(.016,5);
   // Fixed camera, real carrier and real sunlight in the home belt.
   const center=b.station.position.clone(),toSun=new V(...b.zone.sunDir).normalize();
   b.camera.position.copy(center).add(new V(6500,2900,7200));b.camera.up.set(0,1,0);b.camera.lookAt(center);b.camera.updateMatrixWorld(true);
   drawLighting();return {version:document.getElementById('version').textContent,carrier:b.carrierAsset.state,player:b.playerAsset.state,lighting:{...b.lighting.status},calls:b.renderer.info.render.calls};
  });
  if(directFile){assert.deepEqual(errors,[]);const result={passed:true,mode:'file',gameSHA256:loadedSHA,setup,errors};fs.writeFileSync(path.join(out,'file-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));return;}
  await page.screenshot({path:path.join(out,'previews/carrier.png')});
  await page.evaluate(()=>{const b=BeltRunner,V=THREE.Vector3,dir=new V(...b.zone.sunDir).normalize(),side=new V().crossVectors(dir,new V(0,1,0)).normalize();b.camera.position.copy(b.station.position).addScaledVector(dir,9000).addScaledVector(side,4200);b.camera.lookAt(b.station.position);b.camera.updateMatrixWorld(true);drawLighting();});
  await page.screenshot({path:path.join(out,'previews/carrier-sunlit.png')});
  assert.deepEqual(errors,[],errors.join('\n').slice(0,4000));
  const rocks=await page.evaluate(()=>{
   const b=BeltRunner,V=THREE.Vector3;
   b.asteroids.forEach(a=>a.dead=true);b.scenery.forEach(a=>a.dead=true);
   const center=b.station.position.clone().add(new V(22000,7000,14000));
   const shapes=['lumpy','cratered','chunk','hollow','potato','bean'],ores=['iron','copper','gold','platinum','crystal'];
   for(let i=0;i<5;i++){
    const group=new THREE.Group();group.position.copy(center).add(new V((i-2)*520,(i%2)*110,0));group.rotation.set(.2+i*.5,.3+i*.4,.1+i*.2);
    const a={shape:shapes[i],seed:i+2.1,baseR:190,r:190,group,pos:group.position,ore:ores[i],barren:false,dead:false};b.rockAssets.register(a);b.asteroids.push(a);
   }
   b.camera.position.copy(center).add(new V(1200,560,-1750));b.camera.lookAt(center);b.camera.updateMatrixWorld(true);drawLighting();
   return {...b.rockAssets.status,lighting:{...b.lighting.status},calls:b.renderer.info.render.calls};
  });
  await page.screenshot({path:path.join(out,'previews/ore-reflections.png')});
  const sun=await page.evaluate(()=>{
   const b=BeltRunner,V=THREE.Vector3,dir=new V(...b.zone.sunDir).normalize();
   b.camera.position.copy(b.station.position).add(new V(22000,7000,14000));b.camera.lookAt(b.camera.position.clone().add(dir));b.camera.updateMatrixWorld(true);drawLighting();
   return {...b.lighting.status};
  });
  await page.screenshot({path:path.join(out,'previews/sun.png')});
  const hangar=await page.evaluate(()=>{
   const b=BeltRunner,V=THREE.Vector3;
   const world=p=>p.applyQuaternion(b.STATION.q).add(b.station.position);
   b.camera.position.copy(world(new V(260,30,1250)));b.camera.lookAt(world(new V(0,-45,0)));b.camera.updateMatrixWorld(true);drawLighting();
   return {lights:b.stationPointLights.map(l=>({intensity:l.intensity,color:l.color.getHexString()})),...b.lighting.status};
  });
  await page.screenshot({path:path.join(out,'previews/hangar.png')});
  assert.deepEqual(errors,[],errors.join('\n').slice(0,4000));
  const physical=await page.evaluate(()=>{
   const b=BeltRunner,V=THREE.Vector3,L=b.lighting,dir=new V(...b.zone.sunDir).normalize(),right=new V().crossVectors(dir,new V(0,1,0)).normalize();
   const origin=new V(500000,120000,500000),receiver=new THREE.Mesh(new THREE.PlaneGeometry(600,600),new THREE.MeshStandardMaterial({color:0xc0c0c0,roughness:1}));
   receiver.position.copy(origin);receiver.quaternion.setFromUnitVectors(new V(0,0,1),dir);b.scene.add(receiver);
   const blocker=new THREE.Mesh(new THREE.BoxGeometry(80,80,80),new THREE.MeshStandardMaterial({color:0x444444}));blocker.position.copy(origin).addScaledVector(dir,140);b.scene.add(blocker);
   b.camera.position.copy(origin).addScaledVector(dir,500).addScaledVector(right,650);b.camera.lookAt(origin);b.camera.updateMatrixWorld(true);
   const sample=()=>{const gl=b.renderer.getContext(),p=new Uint8Array(4);gl.readPixels(Math.floor(gl.drawingBufferWidth/2),Math.floor(gl.drawingBufferHeight/2),1,1,gl.RGBA,gl.UNSIGNED_BYTE,p);return (p[0]+p[1]+p[2])/3;};
   drawLighting();const shadow=sample();blocker.visible=false;drawLighting();const lit=sample();
   if(!(lit>100&&shadow<lit*.65))throw Error('Shadow map does not darken a blocked surface: '+JSON.stringify({shadow,lit}));
   // Move the same receiver into the planet's umbra; sunlight must be blocked
   // even though a planet this large is outside the local shadow map.
   receiver.position.copy(dir).multiplyScalar(-b.planets[0].r*1.7);b.camera.position.copy(receiver.position).addScaledVector(dir,500).addScaledVector(right,650);b.camera.lookAt(receiver.position);b.camera.updateMatrixWorld(true);drawLighting();const eclipse=sample();
   if(!(eclipse<lit*.65)||L.status.sunVisible!==0)throw Error('Planet eclipse failed: '+JSON.stringify({eclipse,lit,visible:L.status.sunVisible}));
   b.scene.remove(receiver,blocker);receiver.geometry.dispose();receiver.material.dispose();blocker.geometry.dispose();blocker.material.dispose();
   const qualities=[];for(const quality of ['low','high','balanced']){window.testQuality=quality;drawLighting();qualities.push({quality,size:L.status.shadowSize});}window.testQuality='balanced';
   return {shadow,lit,eclipse,qualities};
  });
  const zones=await page.evaluate(()=>{
   const b=BeltRunner,checks=[];for(const z of b.ZONES){b.loadZone(z);b.camera.position.copy(b.station.position).add(new THREE.Vector3(5000,2000,6000));b.camera.lookAt(b.station.position);b.camera.updateMatrixWorld(true);drawLighting();checks.push({zone:z.id,exposure:b.renderer.toneMappingExposure,shadowMap:!!b.lighting.sun.shadow.map,models:b.rockAssets.status.models});}return checks;
  });
  const gameplay=await page.evaluate(()=>{
   const b=BeltRunner,V=THREE.Vector3;b.loadZone(b.ZONES.find(z=>z.id==='kessler'));
   const pos=b.station.position.clone().add(new V(15000,5000,15000));
   const a=b.makeAsteroid(b.asteroids[0].belt,null,null,{cls:'small',r:100,ore:'iron',barren:false,pos,amount:80});a.hp=a.hpMax=100000;a.free=true;a.vel=new V();b.asteroids.push(a);
   b.ship.q.identity();b.keys[' ']=true;const hp=a.hp;
   for(let i=0;i<140;i++){b.ship.pos.copy(a.pos).add(new V(0,0,-a.boundR-150));b.ship.vel.set(0,0,0);b.update(.05);b.updateVisuals(.05,10+i*.05);}
   if(a.hp>=hp||b.heatFx.rock!==a||!a.asset.heat)throw Error('Held trigger no longer mines and heats the rock');
   const heldDamage=hp-a.hp,heat=b.heatFx.heat;b.keys[' ']=false;const releasedHp=a.hp;
   for(let i=0;i<10;i++){b.ship.pos.copy(a.pos).add(new V(0,0,-a.boundR-150));b.ship.vel.set(0,0,0);b.update(.05);b.updateVisuals(.05,18+i*.05);}
   if(a.hp!==releasedHp)throw Error('Releasing the trigger did not stop mining');
   drawLighting();const start=performance.now();for(let i=0;i<30;i++){b.lighting.update({camera:b.camera,station:b.station,asteroids:b.asteroids,scenery:b.scenery,rockAssets:b.rockAssets,dt:.016});b.rockAssets.render(b.camera,'balanced');}
   return {heldDamage,heat,releasedDamage:releasedHp-a.hp,lightingAndBatchCpuMs:(performance.now()-start)/30,drawCalls:b.renderer.info.render.calls};
  });
  assert.deepEqual(errors,[],errors.join('\n').slice(0,4000));
  assert.equal(loadedSHA,require('node:crypto').createHash('sha256').update(fs.readFileSync(path.join(root,'belt-runner-3d.html'))).digest('hex'),'Concurrent game edit during verification; rerun against the latest version');
  const results={passed:true,gameSHA256:loadedSHA,setup,rocks,sun,hangar,physical,zones,gameplay,errors};
  fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify(results,null,2)+'\n');console.log(JSON.stringify(results,null,2));
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
