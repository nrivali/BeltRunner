const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto'),assert=require('node:assert/strict'),vm=require('node:vm');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'assets/cinematics'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const game=path.join(root,'belt-runner-3d.html'),gameSHA=sha(fs.readFileSync(game)),shotSHA=sha(fs.readFileSync(path.join(dir,'camera-shots.js')));
fs.mkdirSync(path.join(dir,'previews'),{recursive:true});
const server=http.createServer((req,res)=>{const p=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(!p.startsWith(root+path.sep))return res.writeHead(403).end();fs.readFile(p,(e,b)=>{if(e)return res.writeHead(404).end();res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':'application/octet-stream');res.end(b);});});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl']});
try{
 const page=await browser.newPage({viewport:{width:1280,height:800}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/WebGLProgram|Shader Error/.test(m.text()))errors.push(m.text());});
 await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;let seed=9184;Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};});await page.route(/^https:\/\//,r=>r.abort());
 await page.goto(`http://127.0.0.1:${server.address().port}/belt-runner-3d.html?debug`,{waitUntil:'load',timeout:60000});
 await page.waitForFunction(()=>window.BeltRunner?.carrierAsset.state==='ready'&&BeltRunner.playerAsset.state==='ready'&&BeltRunner.rockAssets.ready,null,{polling:100,timeout:60000});
 console.log(await page.evaluate(()=>{
  const b=BeltRunner,check=(v,s)=>{if(!v)throw Error(s);};b.state.tut=-1;b.startGame();Object.assign(b.state.cargo,{copper:37,iron:12});b.state.up.range=1;
  window.shotTest={check,checks:[],metrics:{},snapshots:{},initial:JSON.stringify({cargo:b.state.cargo,up:b.state.up}),
   tick(dt=1/30){b.update(dt);b.updateVisuals(dt,b.state.time);},
   render(){b.lighting.update({camera:b.camera,station:b.station,quality:'balanced',asteroids:b.asteroids,scenery:b.scenery,rockAssets:b.rockAssets,dt:.1});b.rockAssets.render(b.camera,'balanced');b.renderer.render(b.scene,b.camera);},
   warpUntil(t){let n=0;while(b.warpCut&&b.warpCut.t<t-1e-7&&n++<1000)this.tick(Math.min(1/30,t-b.warpCut.t));},
   pose(){return {position:b.camera.position.clone(),rotation:b.camera.quaternion.clone(),offset:b.camera.position.clone().sub(b.ship.pos)};},
   delta(a){return {position:b.camera.position.distanceTo(a.position),angle:b.camera.quaternion.angleTo(a.rotation),relative:b.camera.position.clone().sub(b.ship.pos).distanceTo(a.offset)};},
   cutUntil(t){let n=0;while(b.cut&&b.cut.t<t-1e-7&&n++<1500)this.tick(Math.min(1/30,t-b.cut.t));},
   clean(){check(!b.hyperspace.root.visible,'Warp FX stuck');check(b.camera.fov===62,'FOV stuck');check(b.station.scale.distanceTo(new THREE.Vector3(1,1,1))<1e-9,'Hull stretch stuck');},
  };shotTest.tick();const gl=b.renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');b.warpTo(b.ZONES.find(z=>z.hub));return {gpu:ext&&gl.getParameter(ext.UNMASKED_RENDERER_WEBGL),started:'Belt to Hub'};
 }));
 const capture=async name=>{await page.evaluate(()=>shotTest.render());await page.screenshot({path:path.join(dir,'previews',name+'.png')});};
 await page.evaluate(()=>{shotTest.warpUntil(6.24);shotTest.beforeHandoff=shotTest.pose();});await capture('warp-end');
 console.log(await page.evaluate(()=>{const b=BeltRunner,w=shotTest;w.tick(.011);const d=w.delta(w.beforeHandoff);w.check(!!b.cut&&b.cut.world,'Missing colony approach');w.check(d.position<20&&d.angle<.005,'Warp to approach camera jumped: '+JSON.stringify(d));w.check(document.body.classList.contains('in-cut')&&document.getElementById('cine').classList.contains('on'),'Letterbox flashed off between cutscenes');w.metrics.warpToApproach=d;return d;}));await capture('approach-start');
 const hub=await page.evaluate(()=>{
  const b=BeltRunner,w=shotTest;let maxStep=0,maxAngle=0,minRadius=Infinity,frames=0;
  while(b.cut&&b.cut.t<b.cut.dur*.6){const previous=w.pose();w.tick();const d=w.delta(previous);maxStep=Math.max(maxStep,d.position);maxAngle=Math.max(maxAngle,d.angle);minRadius=Math.min(minRadius,b.camera.position.distanceTo(b.ship.pos));frames++;}
  w.hubStats={maxStep,maxAngle,minRadius,frames};return w.hubStats;
 });console.log('Hub approach',hub);await capture('colony-approach');
 console.log(await page.evaluate(()=>{
  const b=BeltRunner,w=shotTest,m=w.hubStats;let final;
  while(b.cut){const previous=w.pose();w.tick();const d=w.delta(previous);m.maxStep=Math.max(m.maxStep,d.position);m.maxAngle=Math.max(m.maxAngle,d.angle);m.minRadius=Math.min(m.minRadius,b.camera.position.distanceTo(b.ship.pos));m.frames++;if(!b.cut)final=d;}
  w.check(m.maxStep<950&&m.maxAngle<.025,'Colony camera has a hard cut: '+JSON.stringify(m));w.check(m.minRadius>13000,'Colony orbit crossed the carrier');w.check(final.position<25&&final.angle<.005,'Colony to holding view jumped: '+JSON.stringify(final));w.check(b.flags.docked&&b.flags.bay==='Holding station','Holding station not reached');w.clean();w.metrics.hub={...m,completion:final};w.checks.push('Continuous warp-to-colony handoff','Continuous colony orbit and holding composition');return w.metrics.hub;
 }));await capture('holding-station');
 console.log(await page.evaluate(()=>{const b=BeltRunner,w=shotTest;b.warpTo(b.ZONES.find(z=>!z.hub));w.warpUntil(6.24);const covered=Number(document.getElementById('cineFade').style.opacity);w.check(covered>.999,'Exterior was not covered before interior edit');w.tick(.011);w.check(!b.warpCut&&b.flags.docked,'Belt arrival failed');const switched=Number(document.getElementById('cineFade').style.opacity);w.check(switched===1,'Camera switched while visible');w.metrics.beltFade={before:covered,atSwitch:switched};return w.metrics.beltFade;}));
 await page.evaluate(()=>{for(let i=0;i<18;i++)shotTest.tick();shotTest.check(Number(document.getElementById('cineFade').style.opacity)===0,'Arrival fade did not clear');shotTest.clean();shotTest.checks.push('Covered exterior-to-hangar edit');});await capture('hangar-arrival');
 // Both hangar mouths, including the approach's hover and descent. Inspect every camera frame.
 for(let visit=0;visit<2;visit++){
  console.log(await page.evaluate(visit=>{
   const b=BeltRunner,w=shotTest,checkCamera=()=>{const p=b.depotLocal(b.camera.position);if(Math.abs(p.z)<900&&Math.abs(p.x)<800&&Math.abs(p.y)<540)w.check(Math.abs(p.x)<405&&p.y<160&&p.y>-166,'Camera crossed hangar wall: '+p.toArray());};
   let before=w.pose();b.startDeparture();b.updateVisuals(0,b.state.time);let start=w.delta(before);w.check(start.position<.01&&start.angle<.001,'Departure camera snapped on start');
   let departureMax=0,n=0,departEnd;while(b.cut&&n++<800){before=w.pose();w.tick();const d=w.delta(before);departureMax=Math.max(departureMax,d.position);checkCamera();if(visit===0&&b.cut?.t>b.cut?.dur*.4&&!w.snapshots.departing){w.render();w.snapshots.departing=b.renderer.domElement.toDataURL('image/png');}if(!b.cut)departEnd=d;}
   w.check(!b.cut&&!b.flags.docked,'Departure failed');w.check(departureMax<100,'Departure camera cut');w.check(departEnd.relative<3&&departEnd.angle<.01,'Flight control handoff jumped: '+JSON.stringify(departEnd));
   before=w.pose();b.startApproach();b.updateVisuals(0,b.state.time);start=w.delta(before);w.check(start.position<.01&&start.angle<.001,'Docking camera snapped on start');
   let approachMax=0,approachAngle=0,approachEnd,peak;n=0;while(b.cut&&n++<1500){before=w.pose();w.tick();const d=w.delta(before);approachMax=Math.max(approachMax,d.position);if(d.angle>approachAngle)peak={t:b.cut?.t,pt:b.cut?.pt};approachAngle=Math.max(approachAngle,d.angle);checkCamera();if(visit===0&&b.cut?.t>b.cut?.dur*.65&&!w.snapshots.docking){w.render();w.snapshots.docking=b.renderer.domElement.toDataURL('image/png');}if(!b.cut)approachEnd=d;}
   w.check(!b.cut&&b.flags.docked,'Docking failed');w.check(approachMax<90&&approachAngle<.075,'Approach camera cut: '+JSON.stringify({approachMax,approachAngle,peak}));w.check(approachEnd.relative<3&&approachEnd.angle<.02,'Pad handoff jumped: '+JSON.stringify(approachEnd));w.check(!document.body.classList.contains('in-cut'),'Cinematic HUD stuck');
   const result={visit,bay:b.flags.bay,departureMax,departEnd,approachMax,approachAngle,approachEnd};w.metrics['hangar'+visit]=result;return result;
  },visit));
 }
 await capture('docked');
 for(const [name,url]of Object.entries(await page.evaluate(()=>shotTest.snapshots)))fs.writeFileSync(path.join(dir,'previews',name+'.png'),Buffer.from(url.split(',')[1],'base64'));
 // Skip each stage through the real input handler, including the fade before belt arrival.
 await page.evaluate(()=>{const b=BeltRunner;b.warpTo(b.ZONES.find(z=>z.hub));shotTest.warpUntil(4.9);});await page.keyboard.press('Space');
 await page.evaluate(()=>{shotTest.tick();shotTest.check(!!BeltRunner.cut,'Skipped warp lost Hub approach');});await page.keyboard.press('Space');
 await page.evaluate(()=>{const b=BeltRunner;shotTest.tick();shotTest.check(b.flags.docked&&!b.cut,'Hub skip did not dock');b.warpTo(b.ZONES.find(z=>!z.hub));shotTest.warpUntil(6.12);});await page.keyboard.press('Space');
 await page.evaluate(()=>{shotTest.tick();shotTest.check(Number(document.getElementById('cineFade').style.opacity)===0,'Skipped warp left a black screen');BeltRunner.startDeparture();shotTest.tick();});await page.keyboard.press('Space');
 await page.evaluate(()=>{shotTest.tick();shotTest.check(!BeltRunner.cut&&!BeltRunner.flags.docked,'Departure skip failed');BeltRunner.startApproach();shotTest.tick();});await page.keyboard.press('Space');
 const report=await page.evaluate(()=>{const b=BeltRunner,w=shotTest;w.tick();w.check(!b.cut&&b.flags.docked,'Approach skip failed');w.check(JSON.stringify({cargo:b.state.cargo,up:b.state.up})===w.initial,'Cargo or upgrades changed');w.clean();w.checks.push('Both hangar mouths and safe camera corridor','Camera continuity into flight and pad views','Warp, colony, departure and docking skips','Cargo and upgrades preserved');return {checks:w.checks,metrics:w.metrics};});
 assert.deepEqual(errors,[]);assert.equal(sha(fs.readFileSync(game)),gameSHA,'Shared game changed during validation');assert.equal(sha(fs.readFileSync(path.join(dir,'camera-shots.js'))),shotSHA);
 const result={passed:true,gameSHA256:gameSHA,cameraShotsSHA256:shotSHA,...report,errors};fs.writeFileSync(path.join(dir,'validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}finally{await browser.close();server.close();}})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
