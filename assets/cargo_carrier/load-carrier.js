/* Load atomically: retain the procedural carrier if an asset is missing or invalid. */
window.loadBeltRunnerCarrier = async function ({station, renderer, install, status}) {
  let model;
  const dispose=root=>root?.traverse(o=>{if(o.isMesh){o.geometry.dispose();const mats=Array.isArray(o.material)?o.material:[o.material];for(const m of mats){for(const v of Object.values(m))if(v?.isTexture)v.dispose();m.dispose();}}});
  try {
    if (!window.BeltRunnerGLTFLoader) throw new Error('GLTF loader unavailable');
    const url=new URL('assets/cargo_carrier/cargo_carrier.glb',document.baseURI);
    let data;
    // fetch the binary where a server allows it; otherwise (file:// play, or a host that will not serve .glb, such as the
    // published artifact page) load the generated base64 script copy of the same file
    try {
      if (location.protocol==='file:') throw new Error('file');
      const response=await fetch(url);if(!response.ok)throw new Error(`Carrier HTTP ${response.status}`);data=await response.arrayBuffer();
    } catch (fetchError) {
      await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=new URL('cargo_carrier.data.js',url).href;s.onload=()=>{s.remove();resolve();};s.onerror=()=>{s.remove();reject(new Error('Carrier data unavailable ('+fetchError.message+')'));};document.head.append(s);});
      data=Uint8Array.from(atob(window.BeltRunnerCarrierData),c=>c.charCodeAt(0)).buffer;
      delete window.BeltRunnerCarrierData;
    }
    const gltf=await new window.BeltRunnerGLTFLoader().parseAsync(data,new URL('.',url).href);
    model=gltf.scene;model.name='cargo_carrier_model';model.updateMatrixWorld(true);
    const names=['hangar_mouth_pos','hangar_mouth_neg','pad_pos','pad_neg','drop_pad','dish_mount','engine_0','engine_1','engine_2','drone_dock_0','drone_dock_1','drone_dock_2','bridge_windows'];
    const anchors={};
    for(const name of names){const node=model.getObjectByName(name);if(!node)throw new Error(`Missing carrier attachment: ${name}`);anchors[name]=node.getWorldPosition(new THREE.Vector3());}
    const materials={};let triangles=0,meshes=0;
    model.traverse(o=>{
      if(!o.isMesh)return;meshes++;triangles+=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3;
      const m=o.material;materials[m.name]=m;
      // The supplied normal map is flat; avoid its per-pixel cost at carrier scale.
      m.normalMap=null;m.envMapIntensity=.85;
      for(const key of ['map','emissiveMap','roughnessMap','metalnessMap'])if(m[key])m[key].anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());
    });
    if(meshes!==4||triangles>40000)throw new Error('Unexpected carrier mesh layout');
    install(model,anchors,materials);
    Object.assign(status,{state:'ready',triangles,meshes,anchors,materials,error:null});
    return model;
  } catch(error) {
    if(model?.parent!==station)dispose(model);
    Object.assign(status,{state:'fallback',error:error.message});
    console.warn('Cargo carrier model could not load; keeping the procedural carrier.',error);
    return null;
  }
};
