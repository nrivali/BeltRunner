const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'assets/cargo_carrier_v3');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try {
  const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/Shader|WebGLProgram/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>window.requestAnimationFrame=()=>0);
  await page.goto('http://127.0.0.1:49280/assets/cargo_carrier_v3/preview.html?debug',{waitUntil:'load'});
  await page.waitForFunction(()=>window.CarrierPreview?.status.state==='ready'&&BeltRunnerHomeworld.state==='ready',null,{polling:100,timeout:60000}).catch(async e=>{throw Error(e.message+' '+JSON.stringify(await page.evaluate(()=>({carrier:window.CarrierPreview?.status,planet:window.BeltRunnerHomeworld?.state,planetError:window.BeltRunnerHomeworld?.error})))+' '+JSON.stringify(errors));});
  const views=[];
  for(const name of ['front','rear','hangar']){
   await page.locator('#'+name).click();
   views.push(await page.evaluate(name=>{const p=CarrierPreview;p.draw(.1);return {name,camera:p.camera.position.toArray(),triangles:p.renderer.info.render.triangles,drawCalls:p.renderer.info.render.calls};},name));
   await page.screenshot({path:path.join(out,'previews','browser-'+name+'.png')});
  }
  await page.locator('#motion').click();
  const paused=await page.evaluate(()=>{const p=CarrierPreview,a=p.rig.yaw.rotation.y;p.draw(2);return a===p.rig.yaw.rotation.y;});assert.ok(paused);
  await page.locator('#motion').click();
  const resumed=await page.evaluate(()=>{const p=CarrierPreview,a=p.rig.yaw.rotation.y;p.draw(2);return a!==p.rig.yaw.rotation.y;});assert.ok(resumed);
  await page.locator('#front').click();await page.mouse.move(1100,550);await page.mouse.down();await page.mouse.move(1250,600);await page.mouse.up();
  const dragged=await page.evaluate(()=>{CarrierPreview.draw(.1);return CarrierPreview.camera.position.toArray();});assert.notDeepEqual(dragged,views[0].camera);
  await page.mouse.wheel(0,-350);const zoomed=await page.evaluate(()=>{CarrierPreview.draw(.1);return CarrierPreview.camera.position.toArray();});assert.notDeepEqual(dragged,zoomed);
  await page.setViewportSize({width:720,height:900});await page.waitForFunction(()=>CarrierPreview.camera.aspect===.8,null,{polling:100});await page.evaluate(()=>CarrierPreview.draw(.1));
  assert.equal(await page.evaluate(()=>CarrierPreview.camera.aspect),.8);assert.deepEqual(errors,[]);
  const result={passed:true,views,paused,resumed,drag:true,zoom:true,responsive:true,errors};fs.writeFileSync(path.join(out,'preview-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(result);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
