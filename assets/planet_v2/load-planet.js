/* Blender terrain + ImageGen-derived PBR maps. One shared asset across zone changes. */
(function () {
  'use strict';
  const T=THREE;
  const api=window.BeltRunnerPlanets={state:'idle',error:null,active:0};
  let promise,template,detailMaterial,atmosphereGeometry;
  const profiles={
    Ferron:{tint:0xfff5e6,air:0x9cbed6,strength:.22},
    Pyra:{tint:0xe47c50,air:0xe8a477,strength:.24},
    Glacia:{tint:0xb8dbff,air:0x93d2ff,strength:.30,ice:true},
    Lumen:{tint:0xcf9ee3,air:0xc3a4ec,strength:.25},
    Midas:{tint:0xf2d08e,air:0xe3c698,strength:.20},
    Null:{tint:0x725979,air:0xa698d9,strength:.15}
  };
  api.profiles=profiles;

  function disposeFallback(group){
    const geometries=new Set(),materials=new Set(),textures=new Set();
    group.traverse(o=>{
      if(o.geometry)geometries.add(o.geometry);
      for(const m of o.material?(Array.isArray(o.material)?o.material:[o.material]):[]){
        materials.add(m);for(const value of Object.values(m))if(value?.isTexture)textures.add(value);
      }
    });
    geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());textures.forEach(t=>t.dispose());
    group.clear();
  }
  async function load(renderer){
    if(promise)return promise;
    api.state='loading';
    promise=(async()=>{
      const url=new URL('assets/planet_v2/planet.glb',document.baseURI);
      const parse=data=>new window.BeltRunnerGLTFLoader().parseAsync(data,new URL('.',url).href);
      let gltf;
      try{
        if(location.protocol==='file:')throw Error('Direct-file loading');
        const response=await fetch(url);if(!response.ok)throw Error('Planet HTTP '+response.status);
        gltf=await parse(await response.arrayBuffer());
      }catch(binaryError){
        await new Promise((resolve,reject)=>{
          const script=document.createElement('script');script.src=new URL('planet.data.js',url).href;
          script.onload=()=>{script.remove();resolve();};
          script.onerror=()=>{script.remove();reject(Error('Planet data unavailable: '+binaryError.message));};
          document.head.append(script);
        });
        try{gltf=await parse(Uint8Array.from(atob(window.BeltRunnerPlanetData),c=>c.charCodeAt(0)).buffer);}
        finally{delete window.BeltRunnerPlanetData;}
      }
      template=gltf.scene.getObjectByName('Ferron_Terrain');
      if(!template?.isMesh||!template.material.map||!template.material.normalMap||!template.material.roughnessMap)throw Error('Incomplete planet PBR asset');
      const detailIndex=gltf.parser.json.materials.findIndex(m=>m.name==='Planet_Detail');
      if(detailIndex<0)throw Error('Missing fine regolith material');
      detailMaterial=await gltf.parser.getDependency('material',detailIndex);
      template.geometry.computeBoundingSphere();
      // Validate the actual vertices against the existing unit collision envelope.
      const position=template.geometry.attributes.position,v=new T.Vector3();let max=0;
      for(let i=0;i<position.count;i++)max=Math.max(max,v.fromBufferAttribute(position,i).length());
      if(max>1.006)throw Error('Planet terrain exceeds collision shell');
      for(const material of [template.material,detailMaterial])for(const key of ['map','normalMap','roughnessMap','metalnessMap'])if(material[key])material[key].anisotropy=Math.min(16,renderer.capabilities.getMaxAnisotropy());
      atmosphereGeometry=new T.SphereGeometry(1.009,128,64);
      Object.assign(api,{state:'ready',triangles:template.geometry.index.count/3,radiusMax:max,error:null});
      return template;
    })().catch(error=>{api.state='fallback';api.error=error.message;console.warn('Planet asset unavailable; retaining procedural terrain.',error);return null;});
    return promise;
  }
  function atmosphere(profile,sunDir){
    return new T.ShaderMaterial({name:'Thin_sunlit_atmosphere',transparent:true,depthWrite:false,
      blending:T.AdditiveBlending,uniforms:{uSun:{value:sunDir},uColor:{value:new T.Color(profile.air)},uStrength:{value:profile.strength}},
      vertexShader:`
        #include <common>
        #include <logdepthbuf_pars_vertex>
        varying vec3 vNormalW;varying vec3 vViewW;
        void main(){
          vec4 world=modelMatrix*vec4(position,1.0);
          vNormalW=normalize(mat3(modelMatrix)*normal);vViewW=cameraPosition-world.xyz;
          vec4 mvPosition=modelViewMatrix*vec4(position,1.0);gl_Position=projectionMatrix*mvPosition;
          #include <logdepthbuf_vertex>
        }`,
      fragmentShader:`
        #include <common>
        #include <logdepthbuf_pars_fragment>
        uniform vec3 uSun;uniform vec3 uColor;uniform float uStrength;
        varying vec3 vNormalW;varying vec3 vViewW;
        void main(){
          #include <logdepthbuf_fragment>
          vec3 n=normalize(vNormalW),v=normalize(vViewW);
          float nv=max(0.0,dot(n,v)),day=smoothstep(-.045,.19,dot(n,uSun));
          float rayleigh=.75*(1.0+pow(dot(v,uSun),2.0));
          float limb=pow(1.0-nv,5.5);
          // Short optical path on the face; longest through the lit edge.
          float density=(limb*.92+pow(1.0-nv,2.0)*.055)*day;
          gl_FragColor=vec4(uColor,density*rayleigh*uStrength);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`});
  }
  function surfaceMaterial(profile){
    const m=template.material.clone();m.name='Planet_regolith';m.color.setHex(profile.tint);
    m.metalness=0;m.roughness=1;m.envMapIntensity=.20;m.normalScale.set(.72,.72);
    m.userData.detailStrength={value:1};
    m.onBeforeCompile=shader=>{
      shader.uniforms.uPlanetDetailStrength=m.userData.detailStrength;
      shader.uniforms.uPlanetDetailColor={value:detailMaterial.map};shader.uniforms.uPlanetDetailNormal={value:detailMaterial.normalMap};
      shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vPlanetLocal;').replace('#include <begin_vertex>','#include <begin_vertex>\nvPlanetLocal=position;');
      shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\nvarying vec3 vPlanetLocal;uniform float uPlanetDetailStrength;uniform sampler2D uPlanetDetailColor;uniform sampler2D uPlanetDetailNormal;')
        .replace('#include <color_fragment>',`#include <color_fragment>
          // A second material scale preserves fine detail when the global map
          // covers thousands of screen pixels. A separate regolith tile avoids
          // repeating the global map's polar caps, basins and UV seams.
          float planetDetail=uPlanetDetailStrength*(1.0-smoothstep(.94,.999,abs(normalize(vPlanetLocal).y)));
          float detailLuma=dot(texture2D(uPlanetDetailColor,vMapUv*36.0).rgb,vec3(.2126,.7152,.0722));
          diffuseColor.rgb*=mix(1.0,.78+.44*smoothstep(.006,.065,detailLuma),planetDetail);
          ${profile.ice?`
          float latitude=abs(normalize(vPlanetLocal).y);
          float frost=smoothstep(.52,.85,latitude+(diffuseColor.r-.2)*.45);
          diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.55,.69,.8),frost*.88);`:''}`)
        .replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
          vec3 fineNormal=texture2D(uPlanetDetailNormal,vNormalMapUv*36.0).xyz*2.0-1.0;
          normal=normalize(normal+tbn*vec3(fineNormal.xy*.26*planetDetail,0.0));`);
    };
    m.customProgramCacheKey=()=> 'planet-detail-v3-'+!!profile.ice;
    return m;
  }
  api.attach=function(p,{renderer,sunDir}){
    p.assetState='loading';
    p.assetReady=load(renderer).then(model=>{
      if(p.removed)return false;
      if(!model){p.assetState='fallback';return false;}
      disposeFallback(p.group);
      const profile=profiles[p.name]||profiles.Ferron;
      const surface=new T.Mesh(template.geometry,surfaceMaterial(profile));
      surface.name='planet_surface';surface.scale.setScalar(p.r);
      surface.userData.solarReceiverOnly=true;
      const air=new T.Mesh(atmosphereGeometry,atmosphere(profile,sunDir));air.name='planet_atmosphere';air.scale.setScalar(p.r);
      p.group.add(surface,air);p.assetState='ready';p.group.userData.planetV2=true;api.active++;
      return true;
    });
    return p.assetReady;
  };
  api.release=function(p){
    p.removed=true;
    if(p.group.userData.planetV2){
      p.group.traverse(o=>{if(o.material)o.material.dispose();});p.group.clear();api.active--;
    }else disposeFallback(p.group);
    // Geometry and textures belong to the single cached asset, not a zone.
  };
})();
