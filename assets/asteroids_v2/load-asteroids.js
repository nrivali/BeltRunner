window.BeltRunnerAsteroids=(()=>{
  const status={state:'loading',error:null,drawCalls:0,triangles:0,visible:0,lodCounts:[0,0,0]},templates=new Map(),batches=new Map();
  let cfg,ready=false,material,stoneMaterial,oreSpecs;
  const V=THREE.Vector3,quat=new THREE.Quaternion(),matrix=new THREE.Matrix4(),scale=new V(),frustum=new THREE.Frustum(),projection=new THREE.Matrix4(),sphere=new THREE.Sphere();
  const baseURL=new URL('assets/asteroids_v2/',document.baseURI);
  async function bytes(){
    try{if(location.protocol==='file:')throw Error('file');const r=await fetch(new URL('asteroids-game.bin.gz',baseURL));if(!r.ok)throw Error('HTTP '+r.status);status.source='binary';return new Uint8Array(await r.arrayBuffer());}
    catch(error){await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=new URL('asteroids-game.data.js',baseURL);s.onload=()=>{s.remove();resolve();};s.onerror=()=>{s.remove();reject(Error('Asteroid data unavailable: '+error.message));};document.head.append(s);});
      if(typeof window.BeltRunnerAsteroidData!=='string')throw Error('Missing asteroid script data');const result=Uint8Array.from(atob(window.BeltRunnerAsteroidData),c=>c.charCodeAt(0));delete window.BeltRunnerAsteroidData;status.source='script';return result;
    }
  }
  async function decode(compressed){
    // Some static hosts advertise Content-Encoding and the browser expands it already.
    const expanded=compressed[0]===66&&compressed[1]===82&&compressed[2]===82&&compressed[3]===50;
    const data=expanded?compressed.buffer.slice(compressed.byteOffset,compressed.byteOffset+compressed.byteLength):await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer(),view=new DataView(data);
    if(view.getUint32(0,true)!==0x32525242)throw Error('Invalid asteroid library');
    const length=view.getUint32(4,true),header=JSON.parse(new TextDecoder().decode(new Uint8Array(data,12,length))),start=12+length;
    if(header.version!==2||header.models.length!==84||Object.keys(header.textures).length!==6||start+view.getUint32(8,true)!==data.byteLength)throw Error('Incomplete asteroid library');
    function array(desc,Type){if(desc.offset<0||desc.length<0||start+desc.offset+desc.length>data.byteLength)throw Error('Invalid asteroid buffer');return new Type(data,start+desc.offset,desc.length/Type.BYTES_PER_ELEMENT);}
    for(const model of header.models){
      const g=new THREE.BufferGeometry(),a=model.attributes;
      g.setAttribute('position',new THREE.BufferAttribute(array(a.position,Float32Array),3));
      g.setAttribute('normal',new THREE.BufferAttribute(array(a.normal,Int16Array),3,true));
      g.setAttribute('tangent',new THREE.BufferAttribute(array(a.tangent,Int16Array),4,true));
      g.setAttribute('uv',new THREE.BufferAttribute(array(a.uv,Float32Array),2));
      g.setAttribute('oreMask',new THREE.BufferAttribute(array(a.ore,Uint8Array),1));
      g.setIndex(new THREE.BufferAttribute(array(a.index,model.indexType===16?Uint16Array:Uint32Array),1));
      if(g.attributes.position.count!==model.count||g.index.count%3)throw Error('Invalid asteroid geometry');
      g.computeBoundingBox();g.computeBoundingSphere();g.name=`${model.key}_LOD${model.lod}`;
      templates.set(g.name,{key:model.key,lod:model.lod,geometry:g,radius:Math.max(...g.boundingBox.min.toArray().map(Math.abs),...g.boundingBox.max.toArray().map(Math.abs)),bound:g.boundingSphere.radius+g.boundingSphere.center.length()});
    }
    const images={};
    await Promise.all(Object.entries(header.textures).map(async([name,desc])=>{
      const url=URL.createObjectURL(new Blob([array(desc,Uint8Array)],{type:'image/png'}));
      try{const t=await new THREE.TextureLoader().loadAsync(url);t.name='Blender asteroid '+name;t.flipY=false;t.colorSpace=name.endsWith('albedo')?THREE.SRGBColorSpace:THREE.NoColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;t.anisotropy=Math.min(4,cfg.renderer.capabilities.getMaxAnisotropy());images[name]=t;}finally{URL.revokeObjectURL(url);}
    }));
    oreSpecs=header.ores;return images;
  }
  function makeMaterial(t){
    const m=new THREE.MeshStandardMaterial({color:0xffffff,map:t.regolith_albedo,normalMap:t.regolith_normal,roughnessMap:t.regolith_metalrough,metalnessMap:t.regolith_metalrough,roughness:1,metalness:0,envMapIntensity:1.05});
    m.name='Blender asteroid surfaces';cfg.heatable(m);const heat=m.onBeforeCompile;
    m.onBeforeCompile=sh=>{
      heat(sh);
      Object.assign(sh.uniforms,{uOreAlbedo:{value:t.ore_albedo},uOreNormal:{value:t.ore_normal},uOreMR:{value:t.ore_metalrough}});
      sh.vertexShader=sh.vertexShader.replace('#include <common>',`#include <common>
attribute float oreMask; attribute vec4 instanceRock;
varying float vOreMask; varying vec4 vRockParameters; varying vec3 vOreTint;
`).replace('#include <begin_vertex>',`#include <begin_vertex>
vOreMask=oreMask;vRockParameters=instanceRock;vOreTint=instanceColor;
`).replace('vHeatW=(modelMatrix*vec4(transformed,1.0)).xyz;','vHeatW=(modelMatrix*instanceMatrix*vec4(transformed,1.0)).xyz;');
      sh.fragmentShader=sh.fragmentShader.replace('uniform float uBody;','').replace(/\buBody\b/g,'vRockParameters.z')
        .replace('#include <common>',`#include <common>
varying float vOreMask;varying vec4 vRockParameters;varying vec3 vOreTint;
uniform sampler2D uOreAlbedo;uniform sampler2D uOreNormal;uniform sampler2D uOreMR;
`)
        .replace('#include <color_fragment>','')
        .replace('#include <map_fragment>',`float oreWeight=vOreMask*vRockParameters.w;
diffuseColor.rgb*=mix(texture2D(map,vMapUv).rgb,texture2D(uOreAlbedo,vMapUv).rgb*vOreTint,oreWeight);`)
        .replace('#include <roughnessmap_fragment>',`float roughnessFactor=mix(texture2D(roughnessMap,vRoughnessMapUv).g,texture2D(uOreMR,vRoughnessMapUv).g*vRockParameters.x,oreWeight);`)
        .replace('#include <metalnessmap_fragment>',`float metalnessFactor=texture2D(uOreMR,vMetalnessMapUv).b*vRockParameters.y*oreWeight;`)
        .replace('#include <normal_fragment_maps>',`vec3 mapN=mix(texture2D(normalMap,vNormalMapUv).xyz,texture2D(uOreNormal,vNormalMapUv).xyz,oreWeight)*2.0-1.0;
mapN.xy*=normalScale;normal=normalize(tbn*mapN);`);
    };
    m.customProgramCacheKey=()=>'blender-asteroids-instanced-v2';
    stoneMaterial=new THREE.MeshStandardMaterial({name:'Blender asteroid scrap',color:0xffffff,map:t.regolith_albedo,normalMap:t.regolith_normal,roughnessMap:t.regolith_metalrough,roughness:1,metalness:0,envMapIntensity:.4});cfg.heatable(stoneMaterial);
    return m;
  }
  function register(a,barren=false){
    if(!ready||a.asset)return false;
    const variant=Math.floor(a.seed*997)%2?'B':'A',key=a.shape+'_'+variant,model=templates.get(key+'_LOD0');if(!model)return false;
    const heat=a.hotMat?.userData.uBody?.value||0;
    for(const child of [...a.group.children]){if(child===a.burnMesh)continue;child.traverse(o=>{if(o.geometry)o.geometry.dispose();});a.group.remove(child);}
    if(a.hotMat){a.hotMat.dispose();a.hotMat=null;}
    const spec=oreSpecs[a.ore]||oreSpecs.iron;
    a.asset={key,variant,heat,lod:2,drawn:false,color:new THREE.Color('#'+spec.color),roughness:spec.roughness,metallic:spec.metallic,barren:barren||!!a.barren};
    a.boundR=model.bound*a.baseR;a.bodyGeo=null;a.mat=stoneMaterial;return true;
  }
  function remove(a){if(a.asset){a.asset.drawn=false;delete a.asset;} }
  function batch(key,count){
    let b=batches.get(key);if(b&&b.capacity>=count)return b;
    const capacity=2**Math.ceil(Math.log2(Math.max(16,count))),g=templates.get(key).geometry.clone();
    g.setAttribute('instanceRock',new THREE.InstancedBufferAttribute(new Float32Array(capacity*4),4).setUsage(THREE.DynamicDrawUsage));
    const mesh=new THREE.InstancedMesh(g,material,capacity);mesh.name='asteroid_batch_'+key;mesh.frustumCulled=false;mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);mesh.instanceColor=new THREE.InstancedBufferAttribute(new Float32Array(capacity*3),3).setUsage(THREE.DynamicDrawUsage);
    mesh.matrixAutoUpdate=false;mesh.count=0;cfg.scene.add(mesh);
    if(b){cfg.scene.remove(b.mesh);b.mesh.geometry.dispose();b.mesh.dispose();}
    b={mesh,capacity};batches.set(key,b);return b;
  }
  const lists=new Map();
  function render(camera,quality){
    if(!ready)return;
    camera.updateMatrixWorld(true);projection.multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse);frustum.setFromProjectionMatrix(projection);
    for(const list of lists.values())list.length=0;
    const height=cfg.renderer.domElement.clientHeight||innerHeight,focal=height/(2*Math.tan(camera.fov*Math.PI/360)),q=quality==='low'?1.5:quality==='high'?.8:1;
    let visible=0,triangles=0,calls=0;const lodCounts=[0,0,0];
    function add(a,isScenery){
      if(a.dead)return;if(!a.asset)register(a,isScenery);const state=a.asset;if(!state)return;state.drawn=false;
      sphere.center.copy(a.pos);sphere.radius=a.boundR;if(!frustum.intersectsSphere(sphere))return;
      const distance=Math.max(1,camera.position.distanceTo(a.pos)),pixels=a.boundR*focal/distance;if(pixels<1.25*q)return;
      let lod=pixels>100*q?0:pixels>22*q?1:2;
      if(state.lod===0&&pixels>82*q)lod=0;else if(state.lod===1&&pixels>18*q&&pixels<116*q)lod=1;
      state.lod=lod;state.drawn=true;const key=state.key+'_LOD'+lod;let list=lists.get(key);if(!list){list=[];lists.set(key,list);}list.push(a);visible++;lodCounts[lod]++;
    }
    for(const a of cfg.asteroids())add(a,false);for(const a of cfg.scenery())add(a,true);
    for(const b of batches.values())b.mesh.count=0;
    for(const [key,list] of lists){if(!list.length)continue;const b=batch(key,list.length),m=b.mesh,params=m.geometry.attributes.instanceRock;
      for(let i=0;i<list.length;i++){const a=list[i],s=a.asset;matrix.compose(a.pos,a.group.quaternion,scale.setScalar(a.baseR));m.setMatrixAt(i,matrix);m.setColorAt(i,s.color);params.setXYZW(i,s.roughness,s.metallic,s.heat,s.barren?0:1);}
      m.count=list.length;m.instanceMatrix.needsUpdate=true;m.instanceColor.needsUpdate=true;params.needsUpdate=true;triangles+=m.geometry.index.count/3*m.count;calls++;
    }
    Object.assign(status,{visible,triangles,drawCalls:calls,lodCounts});
  }
  function bvh(a){const t=templates.get(a.asset.key+'_LOD0');if(!t.bvh)t.bvh=window.BeltRunnerRockBVH.build(t.geometry);return t.bvh;}
  function local(a,p){return p.clone().sub(a.pos).applyQuaternion(quat.copy(a.group.quaternion).invert()).divideScalar(a.baseR);}
  function world(a,p){return p.clone().multiplyScalar(a.baseR).applyQuaternion(a.group.quaternion).add(a.pos);}
  function rayHit(a,origin,direction,limit=Infinity){
    const o=local(a,origin),d=direction.clone().applyQuaternion(quat.copy(a.group.quaternion).invert()).normalize(),hit=bvh(a).cast(o,d,limit/a.baseR);
    return hit?{point:world(a,hit.point),distance:hit.distance*a.baseR}:null;
  }
  function inside(a,p){return bvh(a).inside(local(a,p));}
  function contact(a,p,radius){
    const lp=local(a,p),tree=bvh(a),nearest=tree.nearest(lp),r=radius/a.baseR;if(!nearest)return null;
    if(nearest.distance>=r&&!tree.inside(lp))return null;
    const interior=tree.inside(lp),n=interior||nearest.distance<1e-7?nearest.normal:lp.clone().sub(nearest.point).normalize();
    return {position:world(a,nearest.point.clone().addScaledVector(n,r+.002)),normal:n.applyQuaternion(a.group.quaternion).normalize()};
  }
  function aimPoint(a,origin,preferred){
    if(preferred){const direct=rayHit(a,origin,preferred.clone().sub(origin).normalize());if(direct)return direct.point;}
    const p=bvh(a).nearest(local(a,origin));return p?world(a,p.point):a.pos.clone();
  }
  function surfaceSample(a,p){const s=bvh(a).nearest(local(a,p));return {point:world(a,s.point),normal:s.normal.applyQuaternion(a.group.quaternion).normalize()};}
  function radiusAlong(a,direction){const origin=a.pos.clone().addScaledVector(direction,a.boundR*1.01),hit=rayHit(a,origin,direction.clone().negate(),a.boundR*2.02);return hit?Math.max(0,a.boundR*1.01-hit.distance):0;}
  function scrapGeometry(r,seed){if(!ready)return null;const key='lumpy_'+(Math.floor(seed*997)%2?'B':'A')+'_LOD2',g=templates.get(key).geometry.clone();g.scale(r,r,r);return g;}
  async function load(options){
    cfg=options;
    try{if(!window.BeltRunnerRockBVH?.build)throw Error('Asteroid collision helper unavailable');
      const textures=await decode(await bytes());material=makeMaterial(textures);ready=true;
      for(const a of cfg.asteroids())register(a);for(const a of cfg.scenery())register(a,true);
      Object.assign(status,{state:'ready',error:null,models:templates.size,textures:6,oreTypes:Object.keys(oreSpecs).length});return true;
    }catch(error){ready=false;status.state='fallback';status.error=error.message;console.warn('New asteroid assets unavailable; retaining procedural rocks.',error);cfg.fallback?.();return false;}
  }
  return {status,load,register,remove,render,rayHit,inside,contact,aimPoint,surfaceSample,radiusAlong,scrapGeometry,setHeat:(a,h)=>{if(a.asset)a.asset.heat=h;},get ready(){return ready;},get templates(){return templates;},get batches(){return batches;},get material(){return material;}};
})();
