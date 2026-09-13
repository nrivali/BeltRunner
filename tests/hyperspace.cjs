const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict'),crypto=require('node:crypto'),vm=require('node:vm');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'assets/hyperspace'),game=path.join(root,'belt-runner-3d.html'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const gameSHA=sha(fs.readFileSync(game)),fxSHA=sha(fs.readFileSync(path.join(dir,'hyperspace.js')));
const scope={window:{}};vm.runInNewContext(fs.readFileSync(path.join(dir,'hyperspace.js'),'utf8'),scope);const {sample,transitAt,arrivalAt,duration}=scope.window.BeltRunnerHyperspace;
for(let t=0;t<duration+1;t+=.003){const p=sample(t);for(const v of Object.values(p))if(typeof v==='number')assert.ok(Number.isFinite(v));assert.ok(p.coverage>=0&&p.coverage<=1);assert.ok(p.stretch>=1&&p.stretch<4);}
assert.equal(sample(0).phase,'depart');assert.equal(sample(transitAt).phase,'transit');assert.equal(sample(arrivalAt).phase,'arrive');assert.equal(sample(duration).phase,'done');assert.equal(sample(duration).stretch,1);assert.equal(sample(duration).coverage,0);
fs.mkdirSync(path.join(dir,'previews'),{recursive:true});
const server=http.createServer((req,res)=>{const p=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(!p.startsWith(root+path.sep))return res.writeHead(403).end();fs.readFile(p,(e,b)=>{if(e)return res.writeHead(404).end();res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':'application/octet-stream');res.end(b);});});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl']});
try{
 const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/WebGLProgram|Shader Error/.test(m.text()))errors.push(m.text());});
 await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;let seed=28761;Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};});await page.route(/^https:\/\//,r=>r.abort());
 await page.goto(`http://127.0.0.1:${server.address().port}/belt-runner-3d.html?debug`,{waitUntil:'load',timeout:60000});
 await page.waitForFunction(()=>window.BeltRunner?.carrierAsset.state==='ready'&&BeltRunner.playerAsset.state==='ready'&&BeltRunner.rockAssets.ready,null,{polling:100,timeout:60000});
 const init=await page.evaluate(()=>{
  const b=BeltRunner,check=(v,s)=>{if(!v)throw Error(s);};b.state.tut=-1;b.startGame();
  const engines=()=>b.stationEngines.map(s=>({scale:s.scale.toArray(),opacity:s.material.opacity})),baseline=JSON.stringify(engines()),scale=b.station.scale.toArray();
  window.warpTest={checks:[],captures:[],baseline,scale,check,
   tick(dt=.025){b.update(dt);b.updateVisuals(dt,b.state.time);if(b.warpCut){check(b.STATION.vel.length()<1000,'Warp contaminated physical velocity');check(!b.shipGroup.visible,'Player mesh leaked into warp');}},
   advance(t){let i=0;while(b.warpCut&&b.warpCut.t<t-1e-6&&i++<400)this.tick(Math.min(.025,t-b.warpCut.t));},
   render(){b.lighting.update({camera:b.camera,station:b.station,quality:'balanced',asteroids:b.asteroids,scenery:b.scenery,rockAssets:b.rockAssets,dt:.1});b.renderer.render(b.scene,b.camera);},
   begin(z){check(b.flags.docked,'Fixture is not docked');b.warpTo(z);check(b.flags.warping&&!!b.warpCut,'Warp did not start');const W=b.warpCut;b.warpTo(b.ZONES.find(v=>v!==z));check(b.warpCut===W,'Duplicate warp changed destination');},
   finish(label,z){this.advance(7);check(!b.warpCut&&!b.flags.warping,'Warp did not finish');check(b.zone===z,'Wrong destination');check(!b.hyperspace.status.active&&!b.hyperspace.root.visible,'FX did not reset');check(JSON.stringify(engines())===baseline,'Engine glow not restored');check(JSON.stringify(b.station.scale.toArray())===JSON.stringify(scale),'Carrier stretch not restored');check(b.camera.fov===62,'FOV did not reset');check(b.station.position.distanceTo(b.STATION.pos)<.01,'Render position did not restore');
    if(!z.hub){check(b.flags.docked&&b.flags.bay==='Dock 1','Belt arrival lost dock');check(b.depotLocal(b.ship.pos).distanceTo(b.DEPOT.bays[0].parkL)<.1,'Not at bay pad');check(!document.body.classList.contains('in-cut'),'Letterbox stuck');}
    else check(!!b.cut&&b.cut.world&&!b.flags.docked,'Hub arrival did not hand off to approach');this.checks.push(label);},
   capture(label){this.render();const W=b.warpCut;const c={label,time:W.t,phase:W.phase,stretch:b.station.scale.x,offset:W.pose.offset,fov:b.camera.fov,coverage:W.pose.coverage,engineGain:W.pose.engineGain};
    if(label==='tunnel'){const gl=b.renderer.getContext(),size=gl.drawingBufferWidth*gl.drawingBufferHeight*4,a=new Uint8Array(size),d=new Uint8Array(size),ribbons=b.hyperspace.root.getObjectByName('hyperspace_star_streaks');gl.readPixels(0,0,gl.drawingBufferWidth,gl.drawingBufferHeight,gl.RGBA,gl.UNSIGNED_BYTE,a);ribbons.visible=false;b.renderer.render(b.scene,b.camera);gl.readPixels(0,0,gl.drawingBufferWidth,gl.drawingBufferHeight,gl.RGBA,gl.UNSIGNED_BYTE,d);ribbons.visible=true;b.renderer.render(b.scene,b.camera);let changed=0;for(let i=0;i<size;i+=4)if(Math.abs(a[i]-d[i])+Math.abs(a[i+1]-d[i+1])+Math.abs(a[i+2]-d[i+2])>20)changed++;check(changed>1000,'Star ribbons are not visible');c.visibleStarPixels=changed;}
    this.captures.push(c);return c;}
  };
  // Start with known cargo and upgrades; the new visual should not touch them.
  warpTest.cargo=JSON.stringify(b.state.cargo);warpTest.up=JSON.stringify(b.state.up);warpTest.depot=JSON.stringify(b.state.depot);
  warpTest.tick(.01);const gl=b.renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');return {gpu:ext&&gl.getParameter(ext.UNMASKED_RENDERER_WEBGL),zone:b.zone.id,engines:b.stationEngines.length};
 });console.log('Loaded',JSON.stringify(init));
 const skipApproach=async()=>{if(await page.evaluate(()=>!!BeltRunner.cut)){await page.keyboard.press('Space');await page.evaluate(()=>{warpTest.tick();warpTest.check(BeltRunner.flags.docked&&!BeltRunner.cut,'Hub approach skip failed');});}};
 await page.evaluate(()=>{const b=BeltRunner,z=b.ZONES.find(z=>z.hub);warpTest.begin(z);warpTest.destination=z;});
 for(const [label,t]of [['charge',1.25],['launch',1.73],['jump',1.94],['tunnel',3.2],['arrival',4.69],['settled',5.35]]){
  console.log(JSON.stringify(await page.evaluate(({label,t})=>{warpTest.advance(t);return warpTest.capture(label);},{label,t})));
  await page.screenshot({path:path.join(dir,'previews',label+'.png')});
 }
 await page.evaluate(()=>{warpTest.finish('Belt to Hub',warpTest.destination);const b=BeltRunner;warpTest.check(JSON.stringify(b.state.cargo)===warpTest.cargo,'Cargo changed');warpTest.check(JSON.stringify(b.state.up)===warpTest.up,'Upgrades changed');warpTest.check(JSON.stringify(b.state.depot)===warpTest.depot,'Depot upgrades changed');});
 await skipApproach();
 // Space is exercised through the real keyboard handler at every distinct phase.
 for(const [label,t]of [['charge',.4],['launch',1.75],['transit',3],['arrival',4.7]]){
  await page.evaluate(t=>{const b=BeltRunner;warpTest.destination=b.ZONES.find(z=>z!==b.zone);warpTest.begin(warpTest.destination);warpTest.advance(t);},t);
  await page.keyboard.press('Space');await page.evaluate(label=>{warpTest.tick();warpTest.finish('Space skip during '+label,warpTest.destination);},label);await skipApproach();
 }
 await page.evaluate(()=>{const b=BeltRunner;warpTest.check(b.flags.bay==='Holding station','Wrong Hub berth');warpTest.destination=b.ZONES.find(z=>!z.hub);warpTest.begin(warpTest.destination);warpTest.finish('Hub to belt',warpTest.destination);});
 const report=await page.evaluate(()=>{
  const b=BeltRunner,w=warpTest;w.check(!document.getElementById('warp'),'Legacy spinning overlay remains');
  // Preserve the fixed resources between jumps, and limit the low quality streak draw.
  const fx=b.hyperspace,g=fx.root.getObjectByName('hyperspace_star_streaks').geometry,id=g.uuid,pose=BeltRunnerHyperspace.sample(3),args={pose,time:3,camera:b.camera,nose:new THREE.Vector3(1,0,0),quality:'low'};
  fx.update(args);w.check(g.drawRange.count===256*6,'Low quality budget ignored');fx.update({...args,quality:'balanced'});w.check(g.drawRange.count===640*6&&g.uuid===id,'FX buffers were recreated');fx.reset();
  // Instantiate the same effect with reduced-motion preference to verify its shader controls.
  const match=window.matchMedia;window.matchMedia=()=>({matches:true});const reduced=createBeltRunnerHyperspace({scene:b.scene,renderer:b.renderer});window.matchMedia=match;reduced.update(args);const u=reduced.root.getObjectByName('hyperspace_tunnel').material.uniforms;
  w.check(reduced.reducedMotion&&u.uFlash.value===0&&u.uTrails.value===.25&&u.uLength.value<pose.trailLength,'Reduced motion controls failed');reduced.dispose();
  b.warpTo(b.zone);w.check(!b.flags.warping,'Same zone guard failed');b.startDeparture();b.warpTo(b.ZONES.find(z=>z!==b.zone));w.check(!b.flags.warping,'Undocked warp guard failed');
  let n=0;while(b.cut&&n++<500)w.tick(.05);w.check(!b.cut&&!b.flags.docked,'Dock departure regressed');b.startApproach();n=0;while(b.cut&&n++<500)w.tick(.05);w.check(!b.cut&&b.flags.docked,'Dock approach regressed');w.check(b.shipGroup.visible,'Player ship not restored after warp');w.check(Math.abs(b.ship.q.dot(b.DEPOT.bays.find(v=>v.name===b.flags.bay).q))>.999,'Dock orientation changed');
  w.checks.push('Same-zone and undocked guards','Cargo and upgrades preserved','Quality limits and reusable buffers','Reduced motion shader controls','Dock departure and straight-through approach');return {checks:w.checks,captures:w.captures,fx:fx.status,finalZone:b.zone.name};
 });
 assert.deepEqual(errors,[]);assert.equal(sha(fs.readFileSync(game)),gameSHA,'Shared game changed during validation');assert.equal(sha(fs.readFileSync(path.join(dir,'hyperspace.js'))),fxSHA,'FX changed during validation');
 const result={passed:true,gameSHA256:gameSHA,fxSHA256:fxSHA,timelineSamples:Math.ceil((duration+1)/.003),...init,...report,errors};fs.writeFileSync(path.join(dir,'validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}finally{await browser.close();server.close();}})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
