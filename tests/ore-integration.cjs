const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{const p=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}fs.readFile(p,(e,b)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':'application/octet-stream');res.end(b);});});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const results=[];try{
 for(const mode of ['http','file']){
  const page=await browser.newPage(),errors=[],clusterRequests=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().includes('/ore_clusters/'))clusterRequests.push(r.url());});await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;});
  const url=mode==='file'?pathToFileURL(path.join(root,'belt-runner-3d.html')).href:`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
  await page.goto(url+'?debug',{waitUntil:'load'});await page.waitForFunction(()=>window.BeltRunner&&window.BeltRunnerRockSurface?.status.state==='ready',null,{polling:100});
  const result=await page.evaluate(()=>{
   const b=BeltRunner;let checked=0;
   function check(){for(const a of b.asteroids){if(a.dead)continue;if(a.oreDetail)throw Error('Ore protrusion remains');a.group.traverse(o=>{if(o.isMesh&&o.material!==a.mat&&o.material!==a.hotMat)throw Error('Unexpected protruding ore material');});if(!a.mat.userData.asteroidSurface)throw Error('Rock texture missing');if(!a.barren&&!a.mat.emissiveMap)throw Error('Ore veins missing');checked++;}}
   check();const rock=b.asteroids.find(a=>!a.barren&&a.cls==='small');if(!rock)throw Error('No mineable rock');const count=b.drops.length;b.breakRock(rock,false);if(!rock.dead||b.drops.length<=count)throw Error('Mining drops broken');check();
   return {checkedRocks:checked,protrusions:0,texturedSurfaces:true,oreVeins:true,miningDrops:true,version:document.getElementById('version').textContent};
  });assert.deepEqual(clusterRequests,[]);assert.deepEqual(errors,[]);results.push({mode,...result,clusterRequests:0,errors});await page.close();
 }
 fs.writeFileSync(path.join(__dirname,'ore-integration-results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
}finally{await browser.close();server.close();}})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
