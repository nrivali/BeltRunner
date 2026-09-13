/* Meridian: cached Blender globe, ImageGen biomes/clouds, sunlit air and night lights. */
(function(){
  'use strict';
  const T=THREE,api=window.BeltRunnerHomeworld={state:'idle',active:0,error:null};
  const fallbackGeometry=new T.SphereGeometry(1,128,64),airGeometry=new T.SphereGeometry(1.018,128,64);
  let promise,model;
  function airMaterial(sunDir){
    return new T.ShaderMaterial({name:'Meridian_blue_atmosphere',transparent:true,depthWrite:false,blending:T.AdditiveBlending,
      uniforms:{uSun:{value:sunDir}},
      vertexShader:`#include <common>
        #include <logdepthbuf_pars_vertex>
        varying vec3 vAirNormal;varying vec3 vAirView;
        void main(){vec4 world=modelMatrix*vec4(position,1.0);vAirNormal=normalize(mat3(modelMatrix)*normal);vAirView=cameraPosition-world.xyz;
          vec4 mvPosition=modelViewMatrix*vec4(position,1.0);gl_Position=projectionMatrix*mvPosition;
          #include <logdepthbuf_vertex>
        }`,
      fragmentShader:`#include <common>
        #include <logdepthbuf_pars_fragment>
        uniform vec3 uSun;varying vec3 vAirNormal;varying vec3 vAirView;
        void main(){
          #include <logdepthbuf_fragment>
          vec3 n=normalize(vAirNormal),v=normalize(vAirView);float ns=dot(n,uSun),nv=max(0.0,dot(n,v));
          float day=smoothstep(-.12,.22,ns),rim=pow(1.0-nv,4.8);
          vec3 color=mix(vec3(.035,.24,.75),vec3(.25,.60,1.0),smoothstep(0.0,.7,ns));
          gl_FragColor=vec4(color,(rim*.62+pow(1.0-nv,2.0)*.025)*day);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`});
  }
  function fallbackMaterial(){
    const m=new T.MeshStandardMaterial({name:'Meridian_procedural_fallback',color:0xffffff,roughness:.6,metalness:0});
    m.onBeforeCompile=s=>{
      s.vertexShader=s.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vHomeLocal;').replace('#include <begin_vertex>','#include <begin_vertex>\nvHomeLocal=position;');
      s.fragmentShader=s.fragmentShader.replace('#include <common>',`#include <common>
        varying vec3 vHomeLocal;
        float homeHash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
        float homeNoise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
          return mix(mix(mix(homeHash(i),homeHash(i+vec3(1,0,0)),f.x),mix(homeHash(i+vec3(0,1,0)),homeHash(i+vec3(1,1,0)),f.x),f.y),mix(mix(homeHash(i+vec3(0,0,1)),homeHash(i+vec3(1,0,1)),f.x),mix(homeHash(i+vec3(0,1,1)),homeHash(i+vec3(1,1,1)),f.x),f.y),f.z);}`)
        .replace('#include <color_fragment>',`#include <color_fragment>
          vec3 p=normalize(vHomeLocal);float h=homeNoise(p*3.3+7.0)*.65+homeNoise(p*9.0)*.25+homeNoise(p*28.0)*.1;
          float land=smoothstep(.51,.55,h),ice=smoothstep(.84,.97,abs(p.y));
          diffuseColor.rgb=mix(vec3(.008,.048,.15),vec3(.09,.20,.055),land);diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.68,.78,.85),ice);`);
    };
    m.customProgramCacheKey=()=> 'meridian-fallback-v1';return m;
  }
  function clearMaterials(group){group.traverse(o=>{if(o.material)for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose();});group.clear();}
  async function load(renderer){
    if(promise)return promise;
    api.state='loading';
    promise=(async()=>{
      const url=new URL('assets/hub_planet/homeworld.glb',document.baseURI),parse=data=>new window.BeltRunnerGLTFLoader().parseAsync(data,new URL('.',url).href);
      let gltf;
      try{
        if(location.protocol==='file:')throw Error('Direct-file loading');
        const response=await fetch(url);if(!response.ok)throw Error('Homeworld HTTP '+response.status);gltf=await parse(await response.arrayBuffer());
      }catch(binaryError){
        await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=new URL('homeworld.data.js',url).href;s.onload=()=>{s.remove();resolve();};s.onerror=()=>{s.remove();reject(Error('Homeworld data unavailable: '+binaryError.message));};document.head.append(s);});
        try{gltf=await parse(Uint8Array.from(atob(window.BeltRunnerHomeworldData),c=>c.charCodeAt(0)).buffer);}finally{delete window.BeltRunnerHomeworldData;}
      }
      const surface=gltf.scene.getObjectByName('Meridian_Surface'),clouds=gltf.scene.getObjectByName('Meridian_Clouds');
      if(!surface?.material.map||!surface.material.normalMap||!surface.material.roughnessMap||!surface.material.emissiveMap||!clouds?.material.map)throw Error('Incomplete homeworld material layers');
      for(const mesh of [surface,clouds]){
        mesh.geometry.computeBoundingSphere();
        for(const key of ['map','normalMap','roughnessMap','metalnessMap','emissiveMap'])if(mesh.material[key])mesh.material[key].anisotropy=Math.min(16,renderer.capabilities.getMaxAnisotropy());
      }
      if(surface.geometry.boundingSphere.radius>1.006)throw Error('Homeworld exceeds surface collision shell');
      model={surface,clouds};Object.assign(api,{state:'ready',error:null,surfaceTriangles:surface.geometry.index.count/3,cloudTriangles:clouds.geometry.index.count/3});return model;
    })().catch(e=>{api.state='fallback';api.error=e.message;console.warn('Using procedural homeworld.',e);return null;});
    return promise;
  }
  api.attach=function(p,{renderer,sunDir}){
    p.assetState='loading';p.group.userData.homeworld=true;api.active++;
    const fallback=new T.Mesh(fallbackGeometry,fallbackMaterial());fallback.name='homeworld_fallback';fallback.scale.setScalar(p.r);fallback.userData.solarReceiverOnly=true;
    const air=new T.Mesh(airGeometry,airMaterial(sunDir));air.name='homeworld_atmosphere';air.scale.setScalar(p.r);p.group.add(fallback,air);
    p.assetReady=load(renderer).then(asset=>{
      if(p.removed)return false;
      if(!asset){p.assetState='fallback';return false;}
      clearMaterials(p.group);
      const surface=new T.Mesh(asset.surface.geometry,asset.surface.material.clone());surface.name='homeworld_surface';surface.scale.setScalar(p.r);surface.userData.solarReceiverOnly=true;
      const m=surface.material;m.envMapIntensity=.45;m.normalScale.set(.45,.45);m.emissiveIntensity=1.3;
      const cloudAngle={value:0},cloudVisibility={value:1};
      m.onBeforeCompile=s=>{
        s.uniforms.uHomeSun={value:sunDir};s.uniforms.uHomeCloudAngle=cloudAngle;s.uniforms.uHomeCloudVisibility=cloudVisibility;s.uniforms.uHomeCloudMap={value:asset.clouds.material.map};
        s.vertexShader=s.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vHomeNormalW;').replace('#include <begin_vertex>','#include <begin_vertex>\nvHomeNormalW=normalize(mat3(modelMatrix)*normal);');
        s.fragmentShader=s.fragmentShader.replace('#include <common>','#include <common>\nvarying vec3 vHomeNormalW;uniform vec3 uHomeSun;uniform float uHomeCloudAngle;uniform float uHomeCloudVisibility;uniform sampler2D uHomeCloudMap;')
          .replace('#include <color_fragment>',`#include <color_fragment>
            float cloudShade=texture2D(uHomeCloudMap,vec2(fract(vMapUv.x+uHomeCloudAngle),vMapUv.y)).a;
            diffuseColor.rgb*=1.0-cloudShade*.16*uHomeCloudVisibility;`)
          .replace('#include <emissivemap_fragment>',`#include <emissivemap_fragment>
            totalEmissiveRadiance*=1.0-smoothstep(-.14,.04,dot(normalize(vHomeNormalW),uHomeSun));`);
      };
      m.customProgramCacheKey=()=> 'meridian-ocean-cities-v1';
      const clouds=new T.Mesh(asset.clouds.geometry,asset.clouds.material.clone());clouds.name='homeworld_clouds';clouds.scale.setScalar(p.r);clouds.userData.solarReceiverOnly=true;
      Object.assign(clouds.material,{transparent:true,depthWrite:false,alphaTest:0,opacity:.86,roughness:1,metalness:0,envMapIntensity:.08});clouds.material.side=T.FrontSide;
      const atmosphere=new T.Mesh(airGeometry,airMaterial(sunDir));atmosphere.name='homeworld_atmosphere';atmosphere.scale.setScalar(p.r);
      p.group.add(surface,clouds,atmosphere);p.clouds=clouds;p.cloudAngle=cloudAngle;p.cloudVisibility=cloudVisibility;p.assetState='ready';return true;
    });return p.assetReady;
  };
  api.update=function(p,dt){if(p.clouds){p.clouds.rotation.y=(p.clouds.rotation.y+dt*.0025)%(Math.PI*2);p.cloudAngle.value=p.clouds.rotation.y/(Math.PI*2);p.cloudVisibility.value=p.clouds.visible?1:0;}};
  api.release=function(p){p.removed=true;if(p.group.userData.homeworld){clearMaterials(p.group);p.group.userData.homeworld=false;api.active--;p.clouds=null;p.cloudAngle=null;p.cloudVisibility=null;}};
})();
