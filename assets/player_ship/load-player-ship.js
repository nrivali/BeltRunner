window.loadBeltRunnerPlayerShip=async function({renderer,install,status}){
  try{
    if(!window.BeltRunnerGLTFLoader||!window.assembleBeltRunnerPlayerShip)throw new Error('Player ship loader unavailable');
    const url=new URL('assets/player_ship/player_ship.glb',document.baseURI);let data;
    // fetch the binary where a server allows it; otherwise (file:// play, or a host that will not serve .glb) load the base64 script copy
    try{
      if(location.protocol==='file:')throw new Error('file');
      const r=await fetch(url);if(!r.ok)throw new Error(`Player ship HTTP ${r.status}`);data=await r.arrayBuffer();
    }catch(fetchError){
      await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=new URL('player_ship.data.js',url).href;s.onload=()=>{s.remove();resolve();};s.onerror=()=>{s.remove();reject(new Error('Player ship data unavailable ('+fetchError.message+')'));};document.head.append(s);});
      data=Uint8Array.from(atob(window.BeltRunnerPlayerData),c=>c.charCodeAt(0)).buffer;delete window.BeltRunnerPlayerData;
    }
    const gltf=await new BeltRunnerGLTFLoader().parseAsync(data,new URL('.',url).href);
    const api=assembleBeltRunnerPlayerShip(gltf);api.ship.name='player_ship_model';api.materials={};
    for(const name of ['dish_mount','engine_l','engine_r','nav_l','nav_r','focus','mining_dish_yaw','mining_dish_pitch'])if(!api.ship.getObjectByName(name))throw new Error('Missing player attachment: '+name);
    api.ship.traverse(o=>{if(!o.isMesh)return;const m=o.material;api.materials[m.name]=m;m.envMapIntensity=.85;for(const key of ['map','normalMap','emissiveMap','roughnessMap','metalnessMap'])if(m[key])m[key].anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());});
    install(api);Object.assign(status,{state:'ready',error:null,components:api.parts.size});return api;
  }catch(error){Object.assign(status,{state:'fallback',error:error.message});console.warn('Player ship model unavailable; keeping procedural visuals.',error);return null;}
};
