/* Sun, local shadows and exposure for Three r158. No additional downloads. */
window.createBeltRunnerLighting = function ({renderer, scene, sunDir, skyRadius}) {
  const T=THREE, V=T.Vector3;
  const sun=new T.DirectionalLight(0xfff4e4,5.2);
  sun.name='solar_key'; sun.castShadow=true;
  sun.shadow.mapSize.set(2048,2048);
  sun.shadow.bias=-0.00006; sun.shadow.normalBias=1.1;
  sun.shadow.camera.near=10; sun.shadow.camera.far=40000;
  scene.add(sun,sun.target);
  const bounce=new T.HemisphereLight(0xc9ced5,0x494139,.16);
  bounce.name='faint_reflected_light'; scene.add(bounce);
  const ambient=new T.AmbientLight(0xc5c9d0,.025);scene.add(ambient);
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;
  renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;
  const planet={value:new T.Vector4(0,0,0,0)},direction={value:sunDir};
  const status={zone:null,shadowSize:2048,shadowExtent:0,sunVisible:1,exposure:1.05};
  const materials=new WeakSet(),focus=new V(),forward=new V(),right=new V(),up=new V(),relative=new V();
  const ray=new T.Raycaster(),pmrem=new T.PMREMGenerator(renderer);
  let environment=null,profile=null,occlusionClock=1;
  const profiles={
    hub:{color:0xfff6eb,intensity:5.0,radius:.0085,exposure:1.05},
    kessler:{color:0xfff3e3,intensity:5.3,radius:.0090,exposure:1.05},
    cinder:{color:0xffc49a,intensity:6.0,radius:.0140,exposure:1.0},
    frost:{color:0xe3f0ff,intensity:5.1,radius:.0070,exposure:1.05},
    drift:{color:0xf1e8ff,intensity:4.6,radius:.0080,exposure:1.08},
    aurum:{color:0xffe4b6,intensity:5.6,radius:.0100,exposure:1.02},
    sable:{color:0xc4cfff,intensity:2.4,radius:.0050,exposure:1.12}
  };
  // The disk and its small optical halo are separate: opaque geometry can cover
  // the disk, and the halo also disappears when the actual source is eclipsed.
  const vertex=`varying vec2 vSunUv;
#include <common>
#include <logdepthbuf_pars_vertex>
void main(){vSunUv=uv;vec4 mvPosition=modelViewMatrix*vec4(position,1.0);gl_Position=projectionMatrix*mvPosition;
#include <logdepthbuf_vertex>
}`;
  function sunPlane(fragment,additive){
    const material=new T.ShaderMaterial({uniforms:{uColor:{value:new T.Color(1,.97,.9)},uVisibility:{value:1}},vertexShader:vertex,fragmentShader:`
#include <common>
#include <logdepthbuf_pars_fragment>
varying vec2 vSunUv;uniform vec3 uColor;uniform float uVisibility;
void main(){
#include <logdepthbuf_fragment>
${fragment}
}`,transparent:true,depthWrite:false,depthTest:true,toneMapped:false,blending:additive?T.AdditiveBlending:T.NormalBlending});
    const mesh=new T.Mesh(new T.PlaneGeometry(2,2),material);mesh.frustumCulled=false;mesh.name=additive?'solar_glare':'solar_disk';mesh.renderOrder=additive?5:4;scene.add(mesh);return mesh;
  }
  const disk=sunPlane('float r=length(vSunUv*2.0-1.0);float edge=1.0-smoothstep(.985,1.0,r);gl_FragColor=vec4(mix(uColor,vec3(1.0),.78),edge);',false);
  const halo=sunPlane(`vec2 p=vSunUv*2.0-1.0;float r=length(p);
float core=1.15*exp(-r*19.0)+.24*exp(-r*6.0);
float streak=.20*exp(-abs(p.y)*150.0-abs(p.x)*5.0);
float a=sqrt(core+streak)*.8*(1.0-smoothstep(.55,1.0,r))*uVisibility;
gl_FragColor=vec4(uColor,a);`,true);
  halo.material.depthTest=false; // optical glare belongs to the camera, not a cloud in space
  function rebuildEnvironment(){
    const envScene=new T.Scene();
    // A dark neutral reflection field with the sun in the same direction as the
    // direct key. The small HDR source survives roughness-prefiltered reflections.
    const material=new T.ShaderMaterial({side:T.BackSide,uniforms:{uDir:direction,uColor:{value:sun.color.clone()}},vertexShader:'varying vec3 vDirection;void main(){vDirection=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',fragmentShader:`varying vec3 vDirection;uniform vec3 uDir;uniform vec3 uColor;
void main(){vec3 n=normalize(vDirection);float d=dot(n,uDir);float source=smoothstep(cos(.016),cos(.008),d);float reflected=.016+.018*max(0.0,n.y);gl_FragColor=vec4(vec3(reflected)+uColor*source*65.0,1.0);}`});
    const geometry=new T.SphereGeometry(20,32,16);envScene.add(new T.Mesh(geometry,material));
    const next=pmrem.fromScene(envScene,0,1,100);scene.environment=next.texture;
    if(environment)environment.dispose();environment=next;geometry.dispose();material.dispose();
  }
  function setZone(z){
    profile=profiles[z.id]||profiles.kessler;status.zone=z.id;
    sunDir.set(...z.sunDir).normalize();sun.color.setHex(profile.color);sun.intensity=profile.intensity;
    renderer.toneMappingExposure=profile.exposure;status.exposure=profile.exposure;
    scene.background.setHex(z.id==='drift'?0x030206:0x010204);
    scene.fog.color.copy(scene.background);scene.fog.density=z.fog/100*(z.id==='drift'?.22:.055);
    bounce.intensity=z.id==='sable'?.085:.16;
    disk.material.uniforms.uColor.value.copy(sun.color);halo.material.uniforms.uColor.value.copy(sun.color);
    disk.scale.setScalar(skyRadius*profile.radius);halo.scale.setScalar(skyRadius*profile.radius*12);
    const centre=z.planet?.position||[0,0,0];
    planet.value.set(...centre,z.planet?z.planet.r*250:0);occlusionClock=1;
    rebuildEnvironment();
  }
  function patchMaterial(m){
    if(!m||materials.has(m)||!(m.isMeshStandardMaterial||m.isMeshLambertMaterial||m.isMeshPhongMaterial))return;
    materials.add(m);const before=m.onBeforeCompile,cache=m.customProgramCacheKey.bind(m);
    m.onBeforeCompile=function(shader,...args){
      before.call(this,shader,...args);
      shader.uniforms.uSolarPlanet=planet;shader.uniforms.uSolarDirection=direction;
      shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vSolarWorld;')
        .replace('#include <project_vertex>',`#include <project_vertex>
vec4 solarWorld=vec4(transformed,1.0);
#ifdef USE_INSTANCING
solarWorld=instanceMatrix*solarWorld;
#endif
vSolarWorld=(modelMatrix*solarWorld).xyz;`);
      shader.fragmentShader=shader.fragmentShader.replace('#include <common>',`#include <common>
varying vec3 vSolarWorld;uniform vec4 uSolarPlanet;uniform vec3 uSolarDirection;
float planetSunVisibility(){
  vec3 p=uSolarPlanet.xyz-vSolarWorld;float along=dot(p,uSolarDirection);
  if(uSolarPlanet.w<=0.0||along<=0.0)return 1.0;
  float separation=length(p-uSolarDirection*along);
  float penumbra=max(20.0,along*.0045);
  return smoothstep(uSolarPlanet.w-penumbra,uSolarPlanet.w+penumbra,separation);
}`);
      const lights=T.ShaderChunk.lights_fragment_begin.replace('getDirectionalLightInfo( directionalLight, directLight );','getDirectionalLightInfo( directionalLight, directLight );\n directLight.color *= planetSunVisibility();');
      shader.fragmentShader=shader.fragmentShader.replace('#include <lights_fragment_begin>',lights);
    };
    m.customProgramCacheKey=()=>cache()+'-solar-v1';m.needsUpdate=true;
  }
  function prepare(root){
    root.traverse(o=>{
      if(!o.isMesh)return;const list=Array.isArray(o.material)?o.material:[o.material];
      const lit=list.some(m=>m&&(m.isMeshStandardMaterial||m.isMeshLambertMaterial||m.isMeshPhongMaterial));
      if(!lit)return;list.forEach(patchMaterial);o.receiveShadow=true;
      if(o.isInstancedMesh)return;
      if(!o.geometry.boundingSphere)o.geometry.computeBoundingSphere();
      o.castShadow=!o.userData.solarReceiverOnly&&o.geometry.boundingSphere.radius<30000;
    });
  }
  function sourceVisibility(camera,station,rocks,scenery,rockAssets){
    const origin=camera.position,p=planet.value;
    if(p.w){relative.set(p.x,p.y,p.z).sub(origin);const a=relative.dot(sunDir);if(a>0&&relative.addScaledVector(sunDir,-a).length()<p.w)return 0;}
    relative.copy(station.position).sub(origin);const along=relative.dot(sunDir);
    if(along>-5000&&relative.clone().addScaledVector(sunDir,-along).length()<5000){
      ray.set(origin,sunDir);ray.near=2;ray.far=20000;ray.camera=camera;
      const hull=[];station.traverse(o=>{if(o.isMesh&&o.visible&&!o.material.transparent)hull.push(o);});
      if(ray.intersectObjects(hull,false).length)return 0;
    }
    for(const list of [rocks,scenery])for(const a of list){
      if(a.dead)continue;relative.copy(a.pos).sub(origin);const along=relative.dot(sunDir),r=a.boundR||a.baseR;
      if(along<=0||relative.addScaledVector(sunDir,-along).lengthSq()>r*r)continue;
      if(a.asset&&rockAssets?.rayHit(a,origin,sunDir))return 0;
      if(!a.asset)return 0;
    }
    return 1;
  }
  function configureHangar(station){
    station.traverse(o=>{if(o.isPointLight){o.intensity=2600;o.color.setHex(0xffc98c);o.distance=1150;o.decay=1.25;}});
  }
  function update({camera,quality='balanced',station,asteroids=[],scenery=[],rockAssets,dt=.016}){
    if(!profile)return;
    camera.updateMatrixWorld(true);scene.updateMatrixWorld(true);
    disk.position.copy(camera.position).addScaledVector(sunDir,skyRadius);halo.position.copy(disk.position);
    disk.quaternion.copy(camera.quaternion);halo.quaternion.copy(camera.quaternion);
    camera.getWorldDirection(forward);
    const nearCarrier=camera.position.distanceToSquared(station.position)<11000**2;
    const extent=nearCarrier?5600:2400;
    focus.copy(camera.position).addScaledVector(forward,nearCarrier?800:900);
    right.crossVectors(sunDir,new V(0,1,0)).normalize();up.crossVectors(right,sunDir).normalize();
    const size=Math.min(renderer.capabilities.maxTextureSize,quality==='high'?4096:quality==='low'?1024:2048);
    if(sun.shadow.mapSize.x!==size){sun.shadow.mapSize.set(size,size);if(sun.shadow.map){sun.shadow.map.dispose();sun.shadow.map=null;}status.shadowSize=size;}
    // Stabilize the light in world space to avoid crawling shadow texels in flight.
    const texel=extent*2/size;
    focus.addScaledVector(right,Math.round(focus.dot(right)/texel)*texel-focus.dot(right));
    focus.addScaledVector(up,Math.round(focus.dot(up)/texel)*texel-focus.dot(up));
    sun.position.copy(focus).addScaledVector(sunDir,20000);sun.target.position.copy(focus);
    const c=sun.shadow.camera;c.left=c.bottom=-extent;c.right=c.top=extent;c.updateProjectionMatrix();
    status.shadowExtent=extent;sun.shadow.normalBias=nearCarrier?1.3:.65;
    // The asteroid renderer includes nearby off-screen casters in this volume.
    if(rockAssets)rockAssets.shadowRegion={center:focus.clone(),radius:extent*1.75,direction:sunDir};
    occlusionClock+=dt;
    if(occlusionClock>=.1){occlusionClock=0;status.sunVisible=sourceVisibility(camera,station,asteroids,scenery,rockAssets);}
    halo.material.uniforms.uVisibility.value=status.sunVisible;halo.visible=status.sunVisible>0;
    prepare(scene);
  }
  return {sun,bounce,ambient,disk,halo,status,setZone,update,prepare,patchMaterial,configureHangar,profiles};
};
