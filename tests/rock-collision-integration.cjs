// Run with: node tests/rock-collision-integration.cjs [--baseline path/to/previous.html]
// CPU collision timings use an isolated browser; they are not end-to-end GPU FPS.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),file=path.join(root,'belt-runner-3d.html'),source=fs.readFileSync(file,'utf8');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),initialHash=hash(source);
const baselineArg=process.argv.indexOf('--baseline');
const baseline=baselineArg<0?null:fs.readFileSync(path.resolve(process.argv[baselineArg+1]),'utf8');
let instrumented=source;
if(baseline){
  const start=baseline.indexOf('function collideRocks(){'),end=baseline.indexOf('// Rocks ride their orbit rails',start);
  const narrow=s=>s.slice(s.indexOf('function rockPair(a, b){'),s.indexOf('function collideRocks(){'));
  assert.equal(narrow(source),narrow(baseline),'Impact response changed');
  const old=baseline.slice(start,end).replace('function collideRocks(){','function baselineCollideRocks(){');
  instrumented=source.replace('Object.assign(window.BeltRunner,{rockCollisionGrid,',
    'const rockCells=new Map(),ROCK_CELL=1200,BIG_ROCK=500;\n'+old+'\nObject.assign(window.BeltRunner,{baselineCollideRocks,rockCollisionGrid,');
}
const server=http.createServer((req,res)=>{
  const u=new URL(req.url,'http://localhost');
  if(u.pathname==='/belt-runner-3d.html'){res.setHeader('Content-Type','text/html; charset=utf-8');res.end(u.searchParams.has('benchmark')?instrumented:source);return;}
  const p=path.resolve(root,'.'+decodeURIComponent(u.pathname));
  if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  fs.readFile(p,(e,data)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.png')?'image/png':p.endsWith('.jpg')?'image/jpeg':'application/octet-stream');res.end(data);});
});
(async()=>{
  let browser;
  try{
    await new Promise(r=>server.listen(0,'127.0.0.1',r));
    browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
    const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error'&&/Shader|WebGLProgram/.test(m.text()))errors.push(m.text());});
    await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;let s=28761;Math.random=()=>{s=(1664525*s+1013904223)>>>0;return s/4294967296;};});
    const url=`http://127.0.0.1:${server.address().port}/belt-runner-3d.html`;
    await page.goto(url+'?debug'+(baseline?'&benchmark':''),{waitUntil:'load',timeout:60000});
    await page.waitForFunction(()=>window.BeltRunner?.rockAssets.ready&&BeltRunner.carrierAsset.state==='ready'&&BeltRunner.playerAsset.state==='ready'&&BeltRunner.planets[0]?.assetState==='ready',null,{timeout:60000,polling:100});
    const results=await page.evaluate(()=>{
      const b=BeltRunner,V=THREE.Vector3;
      b.update(1/60);
      const snapshot=b.nearRocks.map(a=>({a,pos:a.pos.clone(),vel:a.vel?.clone(),free:a.free,field:a.field}));
      const reset=(drifting=[])=>{
        for(const s of snapshot){s.a.pos.copy(s.pos);s.a.free=s.free;s.a.field=s.field;if(s.vel)s.a.vel.copy(s.vel);else delete s.a.vel;}
        for(const a of drifting){a.free=true;a.vel=new V(0,0,0);a.field=null;}
      };
      const median=xs=>xs.slice().sort((a,b)=>a-b)[Math.floor(xs.length/2)];
      const run=fn=>{const t=performance.now();fn();return performance.now()-t;};
      const bench=[];
      const small=b.nearRocks.filter(a=>a.r<100).slice(0,12),big=b.nearRocks.filter(a=>a.r>500).slice(0,4);
      for(const [name,drifting] of [['passive',[]],['drifting',small.concat(big)]]){
        const before=[],after=[];
        for(let i=0;i<36;i++){
          // Alternate order; restore positions outside the timed section.
          const methods=i%2?['after','before']:['before','after'];
          for(const method of methods){
            if(method==='before'&&!b.baselineCollideRocks)continue;
            reset(drifting); const ms=run(method==='before'?b.baselineCollideRocks:b.collideRocks);
            if(i>=6)(method==='before'?before:after).push(ms);
          }
        }
        reset(drifting); b.collideRocks();
        bench.push({scenario:name,initialDrifting:drifting.length,beforeMedianMs:before.length?median(before):null,afterMedianMs:median(after),indexed:b.rockCollisionGrid.entries.size,queries:b.rockCollisionGrid.stats.queries,candidates:b.rockCollisionGrid.stats.candidates});
      }
      reset();
      // Exercise the real Blender collision surfaces, including a moving colossal.
      const savedNear=b.nearRocks.slice(),savedDebris=b.debris.slice(),fixtures=[];
      const make=(id,shape,r,x,free)=>{
        const group=new THREE.Group();group.position.set(x,0,0);
        const a={id,shape,seed:2,baseR:r,r,group,pos:group.position,ore:'iron',barren:false,dead:false,free,vel:new V(),ang:0,orbit:425000,field:null};
        b.rockAssets.register(a);fixtures.push(a);return a;
      };
      const contacts=[];
      for(const [shape,r] of [['lumpy',50],['boulder',1600],['cratered',12000]]){
        const a=make(-10,shape,r,-1200,true),c=make(-9,'lumpy',40,0,false);
        const ra=b.radiusAlong(a,new V(1,0,0)),rc=b.radiusAlong(c,new V(-1,0,0));
        c.pos.x=a.pos.x+ra+rc-2;a.vel.x=20;
        b.nearRocks.splice(0,b.nearRocks.length,a,c);b.debris.length=0;
        b.collideRocks();
        if(!c.free||Math.abs(c.pos.distanceTo(a.pos)-(ra+rc+4))>.02)throw Error('Blender rock contact failed: '+shape);
        contacts.push({shape,radius:r,separated:true,bothDrifting:c.free});
      }
      const a=make(-8,'boulder',1800,0,false),surface=b.radiusAlong(a,new V(1,0,0));
      const chunk={pos:new V(surface+1,0,0),r:10,vel:new V(-20,0,0),spin:.1};
      b.nearRocks.splice(0,b.nearRocks.length,a);b.debris.splice(0,b.debris.length,chunk);b.collideRocks();
      if(chunk.vel.x<=0||Math.abs(chunk.pos.x-(surface+10))>.02)throw Error('Blender debris bounce failed');
      b.nearRocks.splice(0,b.nearRocks.length,...savedNear);b.debris.splice(0,b.debris.length,...savedDebris);fixtures.forEach(a=>b.rockAssets.remove(a));
      b.updateVisuals(.016,1);b.lighting.update({camera:b.camera,quality:'balanced',station:b.station,asteroids:b.asteroids,scenery:b.scenery,rockAssets:b.rockAssets,dt:.016});
      b.rockAssets.render(b.camera,'balanced');b.renderer.render(b.scene,b.camera);
      return {version:document.getElementById('version').textContent,rocks:b.asteroids.length,near:savedNear.length,large:savedNear.filter(a=>a.r>500).length,planet:b.planets[0].assetState,bench,contacts,debrisBounce:true,drawCalls:b.renderer.info.render.calls};
    });
    assert.equal(results.bench[0].queries,0);assert.equal(results.bench[0].indexed,0);
    // Load the untouched production HTML through file:// as well as HTTP.
    await page.goto(require('node:url').pathToFileURL(file).href+'?debug',{waitUntil:'load',timeout:60000});
    await page.waitForFunction(()=>window.BeltRunner?.rockAssets.ready&&BeltRunner.rockCollisionGrid,null,{timeout:60000,polling:100});
    const fileSmoke=await page.evaluate(()=>{BeltRunner.update(.016);return {version:document.getElementById('version').textContent,rocks:BeltRunner.asteroids.length,collisionGrid:!!BeltRunner.rockCollisionGrid};});
    assert.equal(fileSmoke.version,results.version);assert.equal(fileSmoke.collisionGrid,true);assert.deepEqual(errors,[]);
    assert.equal(hash(fs.readFileSync(file,'utf8')),initialHash,'Game changed during validation');
    const report={passed:true,gameSHA256:initialHash,...results,fileSmoke,errors};
    fs.mkdirSync(path.join(root,'backups'),{recursive:true});fs.writeFileSync(path.join(root,'backups/rock-collision-validation.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
  }finally{if(browser)await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
