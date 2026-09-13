const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'assets/player_ship_v2');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/Shader Error|WebGLProgram/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>window.requestAnimationFrame=()=>0);
  await page.goto('http://127.0.0.1:49280/assets/player_ship_v2/preview.html?debug',{waitUntil:'load'});
  await page.waitForFunction(()=>PlayerPreview.status.state==='ready'&&BeltRunnerHomeworld.state==='ready',null,{polling:100,timeout:60000});
  const variants=await page.evaluate(()=>{
   const p=PlayerPreview,a=p.api;let combinations=0,min=Infinity,max=0;
   for(const wings of ['delta','swept','forward','twin'])for(let laser=1;laser<=3;laser++)for(let cargo=1;cargo<=3;cargo++)for(let engine=1;engine<=3;engine++)for(let scanner=1;scanner<=3;scanner++){
    a.configure({wings,laser,cargo,engine,scanner});let triangles=0;
    a.ship.traverseVisible(o=>{if(o.isMesh)triangles+=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3;});
    if(triangles>24000)throw Error('Ship budget exceeded');min=Math.min(min,triangles);max=Math.max(max,triangles);combinations++;
    if(a.ship.getObjectByName('focus').position.distanceTo(new THREE.Vector3(0,0,1.69+laser*.48))>1e-5)throw Error('Focus does not follow barrel tier');
   }
   a.configure();p.draw(.1);const maps=Object.fromEntries(Object.entries(a.materials).map(([n,m])=>[n,{base:m.map?.image.width,normal:m.normalMap?.image.width,transmission:m.transmission}]));return {combinations,min,max,maps,components:a.parts.size};
  });assert.equal(variants.combinations,324);assert.equal(variants.components,26);assert.ok(variants.maps.glass.transmission>.8);
  for(const name of ['front','rear','cockpit','tool']){await page.locator('#'+name).click();await page.evaluate(()=>PlayerPreview.draw(.1));await page.screenshot({path:path.join(out,'previews','browser-'+name+'.png')});}
  for(const wing of ['delta','swept','forward','twin']){await page.selectOption('#wings',wing);await page.selectOption('#tier','3');await page.locator('#front').click();await page.evaluate(()=>PlayerPreview.draw(.1));await page.screenshot({path:path.join(out,'previews','browser-'+wing+'-tier3.png')});}
  await page.locator('#motion').click();const paused=await page.evaluate(()=>{const p=PlayerPreview,a=p.api.yaw.rotation.y;p.draw(1);return a===p.api.yaw.rotation.y;});assert.ok(paused);
  await page.locator('#motion').click();const moving=await page.evaluate(()=>{const p=PlayerPreview,a=p.api.yaw.rotation.y;p.draw(1);return a!==p.api.yaw.rotation.y;});assert.ok(moving);
  await page.locator('#paint').fill('#638ca4');assert.equal(await page.evaluate(()=>PlayerPreview.api.materials.paint.color.getHexString()),'638ca4');
  const before=await page.evaluate(()=>PlayerPreview.camera.position.toArray());await page.mouse.move(1000,500);await page.mouse.down();await page.mouse.move(1200,550);await page.mouse.up();await page.mouse.wheel(0,-250);
  const after=await page.evaluate(()=>{PlayerPreview.draw(.1);return PlayerPreview.camera.position.toArray();});assert.notDeepEqual(after,before);
  await page.setViewportSize({width:720,height:900});await page.waitForFunction(()=>PlayerPreview.camera.aspect===.8,null,{polling:100});assert.deepEqual(errors,[]);
  const result={passed:true,...variants,views:4,wingViews:4,paused,moving,paint:true,orbitZoom:true,responsive:true,errors};fs.writeFileSync(path.join(out,'preview-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(result);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
