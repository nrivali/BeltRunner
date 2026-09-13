/* Load atomically: retain the procedural carrier if an asset is missing or invalid. */
window.loadBeltRunnerCarrier = async function ({station, renderer, glowTexture, install, status}) {
  let model;
  const dispose=root=>{
    const geometries=new Set(),materials=new Set(),textures=new Set();
    root?.traverse(o=>{if(o.geometry)geometries.add(o.geometry);for(const m of (Array.isArray(o.material)?o.material:[o.material]))if(m)materials.add(m);});
    for(const m of materials){for(const v of Object.values(m))if(v?.isTexture&&v!==glowTexture)textures.add(v);m.dispose();}
    geometries.forEach(g=>g.dispose());textures.forEach(t=>t.dispose());
  };
  try {
    if (!window.BeltRunnerGLTFLoader) throw new Error('GLTF loader unavailable');
    const url=new URL('assets/cargo_carrier_v2/cargo_carrier_assembled.glb',document.baseURI);
    let data,source='glb';
    // fetch the binary where a server allows it; otherwise (file:// play, or a host that will not serve .glb, such as the
    // published artifact page) load the generated base64 script copy of the same file
    try {
      if (location.protocol==='file:') throw new Error('file');
      const response=await fetch(url);if(!response.ok)throw new Error(`Carrier HTTP ${response.status}`);data=await response.arrayBuffer();
    } catch (fetchError) {
      await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=new URL('cargo_carrier_assembled.data.js',url).href;s.onload=()=>{s.remove();resolve();};s.onerror=()=>{s.remove();reject(new Error('Carrier data unavailable ('+fetchError.message+')'));};document.head.append(s);});
      data=Uint8Array.from(atob(window.BeltRunnerCarrierData),c=>c.charCodeAt(0)).buffer;
      delete window.BeltRunnerCarrierData;source='script';
    }
    const gltf=await new window.BeltRunnerGLTFLoader().parseAsync(data,new URL('.',url).href);
    model=gltf.scene;model.name='cargo_carrier_model';model.updateMatrixWorld(true);
    const names=['hangar_mouth_pos','hangar_mouth_neg','pad_pos','pad_neg','drop_pad','dish_mount','engine_0','engine_1','engine_2','drone_dock_0','drone_dock_1','drone_dock_2','bridge_windows'];
    const anchors={};
    for(const name of names){const node=model.getObjectByName(name);if(!node)throw new Error(`Missing carrier attachment: ${name}`);anchors[name]=node.getWorldPosition(new THREE.Vector3());}
    const yaw=model.getObjectByName('dish_yaw'),nativePitch=model.getObjectByName('dish_pitch');
    if(!yaw||!nativePitch||nativePitch.parent!==yaw)throw new Error('Missing carrier dish rig');
    const localMarker=name=>{
      const node=nativePitch.getObjectByName(name);if(!node)throw new Error('Missing dish attachment: '+name);
      return nativePitch.worldToLocal(node.getWorldPosition(new THREE.Vector3()));
    };
    const focus=localMarker('focus'),rims=Array.from({length:6},(_,i)=>localMarker('rim_'+i));
    if(focus.x<=0||Math.abs(focus.z)>.01||yaw.position.distanceTo(anchors.dish_mount)>.01)throw new Error('Invalid carrier dish coordinates');
    const materials={};let triangles=0,meshes=0,dishTriangles=0,dishMeshes=0;
    model.traverse(o=>{
      if(!o.isMesh)return;
      const n=(o.geometry.index?o.geometry.index.count:o.geometry.attributes.position.count)/3;
      let onDish=false;for(let p=o;p;p=p.parent)if(p===yaw){onDish=true;break;}
      if(onDish){dishTriangles+=n;dishMeshes++;}else{triangles+=n;meshes++;}
      const m=o.material;materials[m.name]=m;m.envMapIntensity=.85;
      if(!m.normalMap)throw new Error('Carrier surface normal map missing');
      for(const key of ['map','normalMap','emissiveMap','roughnessMap','metalnessMap'])if(m[key])m[key].anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());
    });
    if(meshes!==4||dishMeshes!==3||triangles+dishTriangles>40000)throw new Error('Unexpected carrier mesh layout');

    // Normalize the authored reflector tilt below a control pivot, keeping the
    // game's aim along local +X while preserving all animated mesh attachments.
    const zAxis=new THREE.Vector3(0,0,1),restPitch=Math.atan2(focus.y,focus.x);
    const pitch=new THREE.Group();pitch.name='carrier_pitch_control';pitch.position.copy(nativePitch.position);
    yaw.add(pitch);pitch.add(nativePitch);nativePitch.position.set(0,0,0);nativePitch.rotation.z=-restPitch;
    focus.applyAxisAngle(zAxis,-restPitch);rims.forEach(p=>p.applyAxisAngle(zAxis,-restPitch));
    const glow=(name,p,color,size)=>{
      const s=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTexture,color,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:.12}));
      s.name=name;s.position.copy(p);s.scale.set(size,size,1);pitch.add(s);return s;
    };
    const rimGlow=rims.map((p,i)=>glow('carrier_rim_glow_'+i,p,0xffd9a0,34));
    const focusGlow=glow('carrier_focus_glow',focus,0x8fe8ff,90);
    const rimBeamMat=new THREE.MeshBasicMaterial({color:0xffc466,transparent:true,opacity:.8,blending:THREE.AdditiveBlending,depthWrite:false});
    const beamGeometry=new THREE.CylinderGeometry(1,1,1,6,1,true),up=new THREE.Vector3(0,1,0);
    const rimBeams=rims.map((p,i)=>{
      const d=focus.clone().sub(p),beam=new THREE.Mesh(beamGeometry,rimBeamMat);
      beam.name='carrier_rim_beam_'+i;beam.position.copy(p).add(focus).multiplyScalar(.5);beam.quaternion.setFromUnitVectors(up,d.clone().normalize());beam.scale.set(3,d.length(),3);beam.visible=false;pitch.add(beam);return beam;
    });
    const rig={yaw,pitch,focus,pitchOff:pitch.position.clone(),rimGlow,focusGlow,rimBeams,rimBeamMat,S:1};
    install(model,anchors,materials,rig);
    Object.assign(status,{state:'ready',revision:2,source,triangles,meshes,dishTriangles,dishMeshes,totalTriangles:triangles+dishTriangles,anchors,materials,error:null});
    return model;
  } catch(error) {
    if(model?.parent!==station)dispose(model);
    Object.assign(status,{state:'fallback',error:error.message});
    console.warn('Cargo carrier model could not load; keeping the procedural carrier.',error);
    return null;
  }
};
