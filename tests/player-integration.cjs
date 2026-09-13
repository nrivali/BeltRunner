const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{const p=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}fs.readFile(p,(e,b)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':p.endsWith('.glb')?'model/gltf-binary':'application/octet-stream');res.end(b);});});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const results=[];
 try{
  for(const mode of ['http','file','missing']){
   const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
   page.on('pageerror',e=>{errors.push(e.message);console.error(mode,e.stack);});page.on('console',m=>{if(m.type()==='error'&&/WebGLProgram|VALIDATE_STATUS|Shader Error/.test(m.text()))errors.push(m.text());});
   await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;});await page.route(/^https:\/\//,r=>r.abort());
   if(mode==='missing'){
    await page.route('**/player_ship.glb',r=>r.fulfill({status:404,body:'missing'}));
    await page.route('**/player_ship.data.js',r=>r.fulfill({status:404,body:'missing'}));
   }
   const url=mode==='file'?pathToFileURL(path.join(root,'belt-runner-3d.html')).href:`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
   await page.goto(url+'?debug',{waitUntil:'load'});await page.waitForFunction(()=>window.BeltRunner?.playerAsset.state && BeltRunner.playerAsset.state!=='loading',null,{polling:100});
   const result=await page.evaluate(()=>({state:BeltRunner.playerAsset.state,error:BeltRunner.playerAsset.error}));assert.equal(result.state,mode==='missing'?'fallback':'ready');
   if(mode!=='missing'){
    Object.assign(result,await page.evaluate(()=>{
     const b=BeltRunner,api=b.playerModel,id=api.ship.uuid;let refits=0,maxTriangles=0;
     const max={laser:4,cargo:5,engine:4,scanner:3};
     for(const wings of ['delta','swept','forward','twin'])for(let laser=0;laser<=4;laser++)for(let cargo=0;cargo<=5;cargo++)for(let engine=0;engine<=4;engine++)for(let scanner=0;scanner<=3;scanner++){
      Object.assign(b.state.up,{laser,cargo,engine,scanner});b.state.custom.wings=wings;b.buildShip();
      if(b.playerModel.ship.uuid!==id)throw new Error('Refit replaced the cached model');
      for(const k in max)if(b.playerAsset.config[k]!==1+Math.round(2*b.state.up[k]/max[k]))throw new Error('Wrong visual upgrade tier');
      let triangles=0;api.ship.traverseVisible(o=>{if(o.isMesh)triangles+=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3;});if(triangles>8000)throw new Error('Budget exceeded');maxTriangles=Math.max(maxTriangles,triangles);refits++;
     }
     b.state.custom.hull='#50a4cc';b.state.custom.trim='#9bf272';b.buildShip();if(api.materials.paint.color.getHexString()!=='50a4cc'||api.accent.value.getHexString()!=='9bf272')throw new Error('Paint controls not applied');
     Object.assign(b.state.up,{laser:0,cargo:0,engine:0,scanner:0});b.state.custom.wings='delta';b.state.custom.hull='#D9DEF0';b.state.custom.trim='#F2A33A';b.buildShip();
     const aimChecks=[];
     for(const p of [[80,30,160],[-80,-30,160],[0,0,200]]){
      const target=new THREE.Vector3(...p).multiplyScalar(3).applyQuaternion(b.ship.q).add(b.ship.pos);const angles=b.shipDishAnglesTo(target);b.shipAim.yaw=angles.yaw;b.shipAim.pitch=angles.pitch;b.setLaserAim(target);b.updateVisuals(.016,1);
      const f=api.ship.getObjectByName('focus'),world=f.getWorldPosition(new THREE.Vector3());const err=world.distanceTo(b.shipDishFocusWorld());if(err>1e-5)throw new Error('Laser does not start at lens');
      const facing=f.getWorldDirection(new THREE.Vector3());const dot=facing.dot(target.clone().sub(world).normalize());if(dot<.999)throw new Error('Dish aims on wrong axis: '+dot);aimChecks.push(dot);
     }
     b.setLaserAim(null);b.ship.thrusting=true;b.updateVisuals(.016,1.21);if(!b.exhausts.every(e=>e.material.opacity>.3))throw new Error('Thrust effects missing');
     if(b.navLights[0].parent.name!=='nav_l'||b.navLights[0].material.color.getHex()!==0xff5a5a)throw new Error('Left nav should be red');
     b.ship.thrusting=false;b.state.tut=-1;b.startGame();b.startDeparture();let ticks=0;while(b.cut&&ticks++<400)b.update(.05);if(b.cut||b.flags.docked)throw new Error('Departure failed');
     b.startApproach();if(!b.cut)throw new Error('Approach failed');ticks=0;while(b.cut&&ticks++<400)b.update(.05);if(b.cut||!b.flags.docked)throw new Error('Docking failed');
     b.updateVisuals(.016,3);
     return {refits,maxTriangles,aimChecks,engines:b.exhausts.length,navLights:b.navLights.length,scale:b.shipGroup.scale.toArray(),departureAndDocking:true};
    }));
    if(mode==='http'){
     await page.evaluate(()=>{const b=BeltRunner;document.querySelectorAll('body > :not(canvas):not(script)').forEach(e=>e.style.display='none');const target=b.ship.pos.clone();b.camera.position.copy(target).add(new THREE.Vector3(70,42,95).applyQuaternion(b.ship.q));b.camera.lookAt(target);b.renderer.render(b.scene,b.camera);});
     await page.screenshot({path:path.join(root,'assets/player_ship/in-game.png')});
    }
   }else{await page.evaluate(()=>{BeltRunner.buildShip();BeltRunner.updateVisuals(.016,1);BeltRunner.renderer.render(BeltRunner.scene,BeltRunner.camera);});}
   assert.deepEqual(errors,[]);results.push({mode,...result,errors});await page.close();
  }
  fs.writeFileSync(path.join(__dirname,'player-integration-results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
