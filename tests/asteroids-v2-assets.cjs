const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),asset=path.join(root,'assets/asteroids_v2');
const report=JSON.parse(fs.readFileSync(path.join(asset,'asset-report.json'))),manifest=JSON.parse(fs.readFileSync(path.join(asset,'manifest.json')));
assert.equal(report.assets.length,84);assert.equal(manifest.shapeFamilies.length,14);assert.equal(manifest.materialVariants.length,18);
for(const a of report.assets){assert.equal(a.nonmanifold_edges,0,a.name);assert.ok(a.ore_surface_fraction>.15&&a.ore_surface_fraction<.5,a.name);assert.ok(a.dimensions.every(d=>d>0&&Number.isFinite(d)));}
for(const shape of manifest.shapeFamilies)for(const v of 'AB'){
 const a=report.assets.filter(a=>a.shape===shape&&a.variant===v).sort((a,b)=>a.lod-b.lod);
 assert.ok(a[0].triangles>a[1].triangles&&a[1].triangles>a[2].triangles);
}
const structural=[];
for(let lod=0;lod<3;lod++){
 const b=fs.readFileSync(path.join(asset,`asteroids_lod${lod}.glb`)),size=b.readUInt32LE(12),j=JSON.parse(b.subarray(20,20+size));
 assert.equal(b.readUInt32LE(0),0x46546c67);assert.equal(b.readUInt32LE(8),b.length);
 assert.equal(j.nodes.length,28);assert.equal(j.meshes.length,28);assert.equal(j.materials.length,18);assert.equal(j.images.length,6);
 assert.deepEqual(j.extensions.KHR_materials_variants.variants.map(v=>v.name),manifest.materialVariants);
 const stone=j.materials.findIndex(m=>m.name==='Barren_Regolith');
 for(const mesh of j.meshes){
  assert.equal(mesh.primitives.length,2,mesh.name);
  for(const p of mesh.primitives){
   for(const k of ['POSITION','NORMAL','TANGENT','TEXCOORD_0'])assert.ok(p.attributes[k]!==undefined,k);
   if(p.material!==stone)assert.equal(p.extensions.KHR_materials_variants.mappings.length,18);
   for(const mapping of p.extensions?.KHR_materials_variants?.mappings||[])assert.ok(mapping.material>=0&&mapping.material<18);
  }
 }
 for(const mat of j.materials){
  const p=mat.pbrMetallicRoughness;
  assert.deepEqual(mat.emissiveFactor,[0,0,0]);assert.equal(mat.doubleSided,false);
  assert.deepEqual(p.baseColorFactor.slice(0,3),mat.extras.color_factor);
  assert.ok(p.baseColorTexture&&p.metallicRoughnessTexture&&mat.normalTexture);
  for(const t of [p.baseColorTexture,p.metallicRoughnessTexture,mat.normalTexture])assert.equal(t.texCoord,0);
 }
 structural.push({lod,bytes:b.length,models:28,materials:18,textures:6});
}
const server=http.createServer((req,res)=>{
 const file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
 if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
 fs.readFile(file,(err,b)=>{if(err){res.writeHead(404).end();return;}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':file.endsWith('.json')?'application/json':file.endsWith('.glb')?'model/gltf-binary':'application/octet-stream');res.end(b);});
});
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/WebGL|shader/i.test(m.text()))errors.push(m.text());});
  await page.goto(`http://127.0.0.1:${server.address().port}/assets/asteroids_v2/preview.html`,{waitUntil:'load'});
  await page.waitForFunction(()=>window.assetPreview?.ready||window.assetPreview?.error,null,{timeout:60000});
  assert.equal(await page.evaluate(()=>assetPreview.error),null);
  await page.click('#spin');
  const runtime=await page.evaluate(async()=>{
   const a=assetPreview,out=[];
   for(let lod=0;lod<3;lod++){
    const gltf=await a.library(lod),materials=await Promise.all(gltf.parser.json.materials.map((_,i)=>gltf.parser.getDependency('material',i)));
    for(const m of materials){
     if(!m.map||!m.normalMap||!m.roughnessMap||!m.metalnessMap)throw Error('PBR maps missing: '+m.name);
     for(const map of [m.map,m.normalMap,m.roughnessMap,m.metalnessMap])if(map.image.width!==1024)throw Error('Texture resolution mismatch');
     if(m.emissive.r+m.emissive.g+m.emissive.b>0)throw Error('Ore is emitting');
    }
    let meshes=0;
    gltf.scene.traverse(m=>{if(m.isMesh){meshes++;for(const key of ['position','normal','uv','tangent']){const att=m.geometry.getAttribute(key);for(const v of att.array)if(!Number.isFinite(v))throw Error('Nonfinite geometry '+m.name);}}});
    if(meshes!==56)throw Error('Missing shape primitive');
    const cave=gltf.scene.getObjectByName(`hollow_A_LOD${lod}`).clone(true),arch=gltf.scene.getObjectByName(`hollow_B_LOD${lod}`).clone(true);
    cave.position.set(0,0,0);arch.position.set(0,0,0);cave.updateMatrixWorld(true);arch.updateMatrixWorld(true);
    const ray=new THREE.Raycaster(new THREE.Vector3(0,-3,0),new THREE.Vector3(0,1,0),0,6);
    const archHits=ray.intersectObject(arch,true),caveHits=ray.intersectObject(cave,true);
    if(archHits.length)throw Error('Arch center blocked at LOD '+lod);
    if(!caveHits.length||caveHits[0].distance<2.4)throw Error('Deep pocket lost at LOD '+lod);
    out.push({lod,models:28,meshes,materials:materials.length,archClear:true,caveDepth:caveHits[0].distance});
   }
   for(const key of ['iron','copper','gold','platinum','crystal','barren','cobalt','beryl','sulfur','emberite','he3','glacite','nebulite','voidpearl','iridium','rhodium','obsidian','darkmatter']){
    document.getElementById('ore').value=key;await a.show();a.render();
   }
   document.getElementById('ore').value='gold';await a.show();a.render();
   return out;
  });
  assert.deepEqual(errors,[]);
  await page.screenshot({path:path.join(asset,'previews','webgl-preview.tmp.png')});
  fs.renameSync(path.join(asset,'previews','webgl-preview.tmp.png'),path.join(asset,'previews','webgl-preview.png'));
  const result={passed:true,structural,runtime,shaderErrors:errors,date:new Date().toISOString()};
  fs.writeFileSync(path.join(asset,'validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
