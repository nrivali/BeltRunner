const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/rival/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const html=`<!doctype html><html><body style="margin:0"><script src="/vendor/three-r158/three.min.js"></script><script src="/vendor/three-r158/GLTFLoader.js"></script><script type="module">
import {assemblePlayerShip} from '/assets/player_ship/assemble-player-ship.js';
try {
 const gltf=await new BeltRunnerGLTFLoader().loadAsync('/assets/player_ship/player_ship.glb');
 const assembled=assemblePlayerShip(gltf);window.assetTest={gltf,...assembled};
} catch(e){window.assetError=e.stack;}
</script></body></html>`;
const server=http.createServer((req,res)=>{if(req.url==='/asset-test'){res.setHeader('Content-Type','text/html');res.end(html);return;}const p=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(!p.startsWith(root+path.sep)){res.writeHead(403).end();return;}fs.readFile(p,(e,b)=>{if(e){res.writeHead(404).end();return;}res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.glb')?'model/gltf-binary':'application/octet-stream');res.end(b);});});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1400,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:'+server.address().port+'/asset-test');await page.waitForFunction(()=>window.assetTest||window.assetError);
  const result=await page.evaluate(()=>{
   if(window.assetError)throw new Error(assetError);
   const {gltf,ship,parts,configure,yaw,pitch}=assetTest;let configurations=0,maxTriangles=0,minTriangles=Infinity,maxRadius=0;
   for(const wings of ['delta','swept','forward','twin'])for(let laser=1;laser<=3;laser++)for(let cargo=1;cargo<=3;cargo++)for(let engine=1;engine<=3;engine++)for(let scanner=1;scanner<=3;scanner++){
    configure({wings,laser,cargo,engine,scanner});ship.updateMatrixWorld(true);let count=0;
    ship.traverseVisible(o=>{if(o.isMesh){count+=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3;const pos=o.geometry.attributes.position;for(let i=0;i<pos.count;i++){const p=new THREE.Vector3().fromBufferAttribute(pos,i).applyMatrix4(o.matrixWorld);maxRadius=Math.max(maxRadius,p.length());}}});
    if(count>8000)throw new Error('Triangle budget exceeded');minTriangles=Math.min(minTriangles,count);maxTriangles=Math.max(maxTriangles,count);
    if(parts.get('laser_barrel_'+laser).parent!==pitch)throw new Error('Barrel is not rigged');
    if(ship.getObjectByName('nav_l').position.x<=0||ship.getObjectByName('nav_r').position.x>=0)throw new Error('Nav orientation incorrect');
    const focus=ship.getObjectByName('focus').getWorldPosition(new THREE.Vector3());if(Math.abs(focus.z-(9.59+laser*.48))>1e-4)throw new Error('Focus location incorrect: '+focus.z);
    configurations++;
   }
   if(maxRadius>16)throw new Error('Ship radius exceeded');
   configure();yaw.rotation.y=Math.PI/2;ship.updateMatrixWorld(true);
   const focus=ship.getObjectByName('focus').getWorldPosition(new THREE.Vector3());if(Math.abs(focus.x-3.07)>1e-3||Math.abs(focus.z-7)>1e-3)throw new Error('Dish yaw axis incorrect');
   yaw.rotation.y=0;ship.updateMatrixWorld(true);
   const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(1400,1000);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;document.body.append(renderer.domElement);
   const scene=new THREE.Scene();scene.background=new THREE.Color(0x202b3d);scene.add(ship);scene.add(new THREE.HemisphereLight(0xc4d9ff,0x4b3d36,2));const key=new THREE.DirectionalLight(0xffe6c8,3);key.position.set(12,25,18);scene.add(key);const fill=new THREE.DirectionalLight(0x9acaff,2);fill.position.set(-20,8,-20);scene.add(fill);
   const cam=new THREE.PerspectiveCamera(38,1.4,.1,1000);cam.position.set(32,20,36);cam.lookAt(0,0,0);renderer.render(scene,cam);
   const textures=new Set();ship.traverse(o=>{if(o.isMesh)for(const value of Object.values(o.material))if(value?.isTexture)textures.add(value.image);});
   if(![...textures].every(im=>im.width===1024&&im.height===1024))throw new Error('Wrong texture resolution');
   return {status:'PASS',threeRevision:THREE.REVISION,configurations,triangleRange:[minTriangles,maxTriangles],maxRadius,componentCount:parts.size,sceneCount:gltf.scenes.length,rendered:true};
  });
  assert.deepEqual(errors,[]);await page.screenshot({path:path.join(root,'assets/player_ship/preview_threejs.png')});
  fs.writeFileSync(path.join(root,'assets/player_ship/browser_validation.json'),JSON.stringify({...result,pageErrors:errors},null,2));console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
