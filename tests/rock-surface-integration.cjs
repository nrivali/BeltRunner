const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'assets/asteroid_surface');
const server=http.createServer((req,res)=>{const p=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}fs.readFile(p,(e,b)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':'application/octet-stream');res.end(b);});});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const results=[];
try{for(const mode of ['http','file','missing']){
 const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/WebGLProgram|Shader Error/.test(m.text()))errors.push(m.text());});await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;});
 let imageRequest,release;const gate=new Promise(r=>release=r);
 if(mode==='http')await page.route('**/asteroid_albedo.png',async r=>{imageRequest=true;await gate;await r.continue();});
 if(mode==='missing')await page.route('**/asteroid_albedo.png',r=>r.fulfill({status:404,body:'missing'}));
 const url=mode==='file'?pathToFileURL(path.join(root,'belt-runner-3d.html')).href:`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
 await page.goto(url+'?debug',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.BeltRunner,null,{polling:100});
 await page.evaluate(()=>{
  const b=BeltRunner;const samples=[b.asteroids.find(a=>a.barren),b.asteroids.find(a=>!a.barren&&!a.cave&&a.mat.flatShading),b.asteroids.find(a=>!a.barren&&!a.cave&&!a.mat.flatShading),b.asteroids.find(a=>a.cave)].filter(Boolean);
  const scene=new THREE.Scene();scene.background=new THREE.Color(0x0b111d);scene.environment=b.scene.environment;scene.add(new THREE.HemisphereLight(0xc7d5ee,0x34303b,2));const sun=new THREE.DirectionalLight(0xffecdb,3.5);sun.position.set(-200,250,250);scene.add(sun);const rim=new THREE.DirectionalLight(0x9ccaff,1);rim.position.set(250,80,-150);scene.add(rim);
  const meshes=samples.map((a,i)=>{const mesh=new THREE.Mesh(a.bodyGeo,a.mat);a.bodyGeo.computeBoundingSphere();const s=64/a.bodyGeo.boundingSphere.radius;mesh.scale.setScalar(s);mesh.position.set((i%2-.5)*160,i<2?90:-70,0);scene.add(mesh);return mesh;});
  const cam=new THREE.PerspectiveCamera(37,1.5,.1,2000);cam.position.set(0,30,590);cam.lookAt(0,5,0);document.querySelectorAll('body > :not(canvas):not(script)').forEach(e=>e.style.display='none');window.rockPreview={scene,cam,meshes,samples};b.renderer.render(scene,cam);
 });
 if(mode==='http'){await page.screenshot({path:path.join(out,'before.png')});release();}
 await page.waitForFunction(()=>window.BeltRunnerRockSurface?.status.state!=='loading',null,{polling:100});
 const result=await page.evaluate(mode=>{
  const api=BeltRunnerRockSurface,b=BeltRunner,p=rockPreview;if(mode==='missing'){if(api.status.state!=='fallback'||p.meshes.some(m=>m.material.userData.asteroidSurface))throw Error('Fallback modified original materials');return {state:api.status.state};}
  if(api.status.state!=='ready')throw Error(api.status.error);
  const textures=new Set();let heatShaders=0;
  for(const mesh of p.meshes){const m=mesh.material;if(!m.userData.asteroidSurface)throw Error('Rock type not upgraded');textures.add(m.map);if(m.isMeshStandardMaterial&&(m.roughness<.85||m.metalness>.05))throw Error('Rock too glossy');const sh={uniforms:{},vertexShader:THREE.ShaderLib[m.isMeshStandardMaterial?'standard':'lambert'].vertexShader,fragmentShader:THREE.ShaderLib[m.isMeshStandardMaterial?'standard':'lambert'].fragmentShader};m.onBeforeCompile(sh);if(!sh.uniforms.uBody||!sh.uniforms.uHeatPos||!sh.fragmentShader.includes('stoneSample'))throw Error('Heat shader lost');heatShaders++;}
  if(textures.size!==1)throw Error('Textures duplicated');
  const source=p.meshes.find(m=>m.material.isMeshStandardMaterial),clone=source.material.clone();let preserved=false;clone.onBeforeCompile=sh=>{preserved=true;sh.uniforms.uBody={value:.5};};api.apply(clone);const probe={uniforms:{},vertexShader:THREE.ShaderLib.standard.vertexShader,fragmentShader:THREE.ShaderLib.standard.fragmentShader};clone.onBeforeCompile(probe);if(!preserved||!probe.fragmentShader.includes('stoneSample'))throw Error('Material clone patch failed');clone.dispose();
  b.renderer.render(p.scene,p.cam);const materials=[...new Set(b.asteroids.map(a=>a.mat))];if(materials.some(m=>!m.userData.asteroidSurface))throw Error('Unconverted asteroid material');
  return {...api.status,sharedTextures:textures.size,rockTypes:p.meshes.length,heatShaders,cloneSupport:true};
 },mode);
 if(mode==='http')await page.screenshot({path:path.join(out,'in-game.png')});assert.deepEqual(errors,[]);results.push({mode,...result,errors});await page.close();
}fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));}finally{await browser.close();server.close();}})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
