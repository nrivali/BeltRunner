/* Blender Garden Habitat: shared PBR geometry and textures, safe asynchronous replacement. */
(function(){
  'use strict';
  const T=THREE,api=window.BeltRunnerGardenColony={state:'idle',error:null,active:0};
  let promise,template;
  function disposeFallback(c){
    const geometries=new Set(),materials=new Set();
    c.group.traverse(o=>{if(o.geometry)geometries.add(o.geometry);if(o.material)for(const m of Array.isArray(o.material)?o.material:[o.material])materials.add(m);});
    geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());c.group.clear();
    // The old materials borrow hullTex/texSoft, so those shared textures are retained.
  }
  function load(renderer){
    if(promise)return promise;
    api.state='loading';
    promise=(async()=>{
      const url=new URL('assets/colony_garden/garden-habitat.glb',document.baseURI);
      const parse=data=>new window.BeltRunnerGLTFLoader().parseAsync(data,new URL('.',url).href);
      let gltf;
      try{
        if(location.protocol==='file:')throw Error('Direct-file loading');
        const response=await fetch(url);if(!response.ok)throw Error('Colony HTTP '+response.status);
        gltf=await parse(await response.arrayBuffer());
      }catch(binaryError){
        await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=new URL('garden-habitat.data.js',url).href;s.onload=()=>{s.remove();resolve();};s.onerror=()=>{s.remove();reject(Error('Colony data unavailable: '+binaryError.message));};document.head.append(s);});
        try{gltf=await parse(Uint8Array.from(atob(window.BeltRunnerGardenColonyData),c=>c.charCodeAt(0)).buffer);}finally{delete window.BeltRunnerGardenColonyData;}
      }
      template=gltf.scene;
      for(const name of ['Habitat_Rings','Civic_Core','Comms_Dish'])if(!template.getObjectByName(name))throw Error('Missing colony assembly '+name);
      let triangles=0,meshes=0;
      template.traverse(o=>{
        if(!o.isMesh)return;meshes++;triangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;
        o.geometry.computeBoundingSphere();o.userData.gardenShared=true;
        for(const m of Array.isArray(o.material)?o.material:[o.material]){
          m.envMapIntensity=.9;
          for(const key of ['map','normalMap','roughnessMap','metalnessMap','emissiveMap'])if(m[key])m[key].anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());
          if(m.name==='Conservatory_glass'){
            m.transparent=true;m.depthWrite=false;m.side=T.FrontSide;o.userData.solarReceiverOnly=true;
            m.onBeforeCompile=s=>{s.fragmentShader=s.fragmentShader.replace('#include <normal_fragment_maps>','#include <normal_fragment_maps>\n diffuseColor.a*=mix(.55,2.5,pow(1.0-abs(dot(normal,normalize(vViewPosition))),3.0));');};
            m.customProgramCacheKey=()=> 'meridian-pressure-glass-v1';
          }
        }
      });
      Object.assign(api,{state:'ready',error:null,triangles,meshes});return template;
    })().catch(e=>{api.state='fallback';api.error=e.message;console.warn('Using original colony geometry.',e);return null;});
    return promise;
  }
  api.attach=function(c,{renderer}){
    c.assetState='loading';api.active++;c.gardenAttached=true;
    c.assetReady=load(renderer).then(asset=>{
      if(c.removed)return false;
      if(!asset){c.assetState='fallback';return false;}
      const angle=c.ring.rotation.y;
      disposeFallback(c);
      const model=asset.clone(true);model.name='Meridian_Garden_Habitat';model.scale.setScalar(1000);c.group.add(model);
      c.ring=model.getObjectByName('Habitat_Rings');c.ring.rotation.y=angle;
      c.dish=model.getObjectByName('Comms_Dish');c.beacons=[];
      model.traverse(o=>{if(o.material?.name==='Navigation_red')c.navMaterial=o.material;});
      c.assetState='ready';c.model=model;return true;
    });return c.assetReady;
  };
  api.release=function(c){
    c.removed=true;
    if(c.gardenAttached){api.active--;c.gardenAttached=false;}
    if(c.assetState==='ready')c.group.clear();else disposeFallback(c);
    // GLB geometry/materials stay cached across zone visits.
  };
  api.update=function(c,t){if(c.navMaterial)c.navMaterial.emissiveIntensity=((t*1.5)%2)<1.3?2.2:.15;};
})();
