const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{const p=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}fs.readFile(p,(e,b)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':'application/octet-stream');res.end(b);});});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const results=[];try{
 for(const mode of ['http','file','missing']){
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/WebGLProgram|Shader Error/.test(m.text()))errors.push(m.text());});await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;});
  if(mode==='missing')await page.route('**/ore_clusters/**/*.glb',r=>r.fulfill({status:404,body:'missing'}));
  const url=mode==='file'?pathToFileURL(path.join(root,'belt-runner-3d.html')).href:`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
  await page.goto(url+'?debug',{waitUntil:'load'});await page.waitForFunction(()=>window.BeltRunner&&window.BeltRunnerOreClusters?.status.state!=='loading',null,{polling:100});
  const result=await page.evaluate(mode=>{
   const b=BeltRunner,api=BeltRunnerOreClusters,rocks=b.asteroids.filter(a=>a.oreDetail);if(rocks.length<10)throw Error('No ore detail rocks');
   if(b.asteroids.some(a=>(a.barren||a.cave)&&a.oreDetail))throw Error('Crystals on barren/cave rock');
   if(mode==='missing'){if(api.status.state!=='fallback')throw Error('Fallback missing');api.beginFrame();api.update(rocks[0].oreDetail,0);if(rocks[0].oreDetail.userData.oreDetail.high)throw Error('Broken detail enabled');return {state:api.status.state,fallback:true};}
   if(api.status.state!=='ready')throw Error(api.status.error);
   for(const a of rocks){api.beginFrame();api.update(a.oreDetail,0);}if(api.status.active!==96)throw Error('Detail budget failed: '+api.status.active);
   let checked=0;const variants=new Set();
   for(const a of rocks){const d=a.oreDetail.userData.oreDetail;if(!d.high)continue;variants.add(d.high.userData.variant);if(d.fallback.visible||d.high.children.length!==3)throw Error('LOD/material batch failure');for(const mesh of d.high.children){if(!mesh.isInstancedMesh||!mesh.material.normalMap)throw Error('Missing textured instances');if(mesh.material.name.startsWith('crystal_')&&mesh.material.color.getHex()!==d.color)throw Error('Ore tint mismatch');const m=new THREE.Matrix4();for(let i=0;i<mesh.count;i++){mesh.getMatrixAt(i,m);const p=new THREE.Vector3().setFromMatrixPosition(m),up=new THREE.Vector3(0,1,0).transformDirection(m);if(up.dot(p)<=0)throw Error('Inward facing crystal');}checked++;}}
   for(const a of rocks)api.update(a.oreDetail,Infinity);if(api.status.active!==0)throw Error('Far detail not released');
   api.beginFrame();for(const a of rocks.slice(0,5))api.update(a.oreDetail,0);if(api.status.active!==2)throw Error('Build pacing failed');for(const a of rocks)api.release(a.oreDetail);
   const a=rocks.find(a=>a.baseR>70&&a.baseR<150)||rocks[0];api.beginFrame();api.update(a.oreDetail,0);b.breakRock(a,false);if(api.status.active!==0||!a.dead)throw Error('Mining cleanup failed');
   const target=rocks.find(r=>!r.dead&&r.baseR>70&&r.baseR<150)||rocks[1];api.beginFrame();api.update(target.oreDetail,0);b.scene.add(target.group);target.group.updateMatrixWorld(true);
   for(const child of b.scene.children)if(child!==target.group&&!child.isLight)child.visible=false;
   const high=target.oreDetail.userData.oreDetail.high,mesh=high.children[0],m=new THREE.Matrix4();mesh.getMatrixAt(0,m);const p=new THREE.Vector3().setFromMatrixPosition(m).applyMatrix4(mesh.matrixWorld),out=p.clone().sub(target.pos).normalize();b.camera.position.copy(p).addScaledVector(out,190).add(new THREE.Vector3(30,45,20));b.camera.lookAt(p);b.camera.near=.1;b.camera.updateProjectionMatrix();document.querySelectorAll('body > :not(canvas):not(script)').forEach(e=>e.style.display='none');b.renderer.render(b.scene,b.camera);
   return {state:api.status.state,checkedMaterialBatches:checked,variants:[...variants],activeLimit:96,buildsPerFrame:2,lodRelease:true,miningCleanup:true};
  },mode);
  if(mode==='http')await page.screenshot({path:path.join(root,'assets/ore_clusters/in-game.png')});assert.deepEqual(errors,[]);results.push({mode,...result,errors});await page.close();
 }
 fs.writeFileSync(path.join(__dirname,'ore-integration-results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
}finally{await browser.close();server.close();}})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
