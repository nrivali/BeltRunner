// Shared asset library; close asteroid details use three instanced material batches.
window.BeltRunnerOreClusters=(()=>{
  const keys=['01_needle','02_fan','03_crown','04_split_spire','05_ridge','06_bloom'];
  const status={state:'loading',error:null,active:0},library=[],materials=new Map();let builds=0;
  async function load(renderer){
    try{
      let embedded;
      // the generated base64 payload serves file:// play and any host that will not serve .glb (the published artifact page)
      const loadEmbedded=async()=>{
        await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=new URL('assets/ore_clusters/ore_clusters.data.js',document.baseURI);s.onload=()=>{s.remove();resolve();};s.onerror=()=>{s.remove();reject(new Error('Ore data unavailable'));};document.head.append(s);});
        embedded=window.BeltRunnerOreData;delete window.BeltRunnerOreData;
      };
      if(location.protocol==='file:')await loadEmbedded();
      else{const probe=await fetch(new URL(`assets/ore_clusters/${keys[0]}/ore_cluster_${keys[0]}.glb`,document.baseURI)).catch(()=>null);if(!probe||!probe.ok)await loadEmbedded();}
      const loaded=await Promise.all(keys.map(async(key,i)=>{
        const url=new URL(`assets/ore_clusters/${key}/ore_cluster_${key}.glb`,document.baseURI);
        let data;if(embedded)data=Uint8Array.from(atob(embedded[i]),c=>c.charCodeAt(0)).buffer;
        else{const r=await fetch(url);if(!r.ok)throw new Error(`Ore GLB HTTP ${r.status}`);data=await r.arrayBuffer();}
        const gltf=await new BeltRunnerGLTFLoader().parseAsync(data,new URL('.',url).href),parts=[];
        gltf.scene.traverse(o=>{if(!o.isMesh)return;const mat=o.material;
          // Opaque PBR retains the mineral highlights without a transmission render pass per frame.
          mat.transmission=0;mat.envMapIntensity=.85;
          for(const field of ['map','normalMap','emissiveMap','roughnessMap','metalnessMap'])if(mat[field])mat[field].anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());
          parts.push({geometry:o.geometry,material:mat});
        });
        if(parts.length!==3)throw new Error('Ore material groups missing');return parts;
      }));
      library.push(...loaded);status.state='ready';status.variants=library.length;
    }catch(e){status.state='fallback';status.error=e.message;console.warn('Ore cluster assets unavailable; using procedural crystals.',e);}
  }
  function detail(bodyGeo,ore,color,cls,radius,fallback){
    const root=new THREE.Group();root.name='ore_surface_detail';root.add(fallback);
    root.userData.oreDetail={bodyGeo,ore,color,cls,radius,fallback,high:null,variant:Math.floor(Math.random()*6),matrices:null};return root;
  }
  function release(root){const d=root.userData.oreDetail;if(!d?.high)return;root.remove(d.high);d.high.traverse(o=>{if(o.isInstancedMesh)o.dispose();});d.high=null;d.fallback.visible=true;status.active--;}
  function update(root,distance){
    const d=root?.userData.oreDetail;if(!d)return;
    if(distance>d.radius+4500){release(root);return;}
    if(d.high||distance>d.radius+3500||status.state!=='ready'||status.active>=96||builds>=2)return;
    const variant=d.variant,parts=library[variant];
    const count=d.cls==='colossal'?4:d.cls==='giant'?3:d.cls==='large'?2:1;
    const pos=d.bodyGeo.attributes.position,index=d.bodyGeo.index,triangles=(index?index.count:pos.count)/3;
    const matrices=d.matrices||[],a=new THREE.Vector3(),b=new THREE.Vector3(),c=new THREE.Vector3(),normal=new THREE.Vector3(),q=new THREE.Quaternion(),roll=new THREE.Quaternion();
    const height=[20,30,40,60,25,45][variant],scale=Math.min(1,d.radius*.6/height);
    for(let i=matrices.length;i<count;i++){
      const face=Math.floor(Math.random()*triangles)*3,at=j=>index?index.getX(face+j):face+j;
      a.fromBufferAttribute(pos,at(0));b.fromBufferAttribute(pos,at(1));c.fromBufferAttribute(pos,at(2));
      normal.crossVectors(b.clone().sub(a),c.clone().sub(a)).normalize();const p=a.clone().add(b).add(c).multiplyScalar(1/3);
      if(normal.dot(p)<0)normal.negate();q.setFromUnitVectors(new THREE.Vector3(0,1,0),normal);roll.setFromAxisAngle(normal,Math.random()*Math.PI*2);q.premultiply(roll);
      p.addScaledVector(normal,-height*scale*.055);matrices.push(new THREE.Matrix4().compose(p,q,new THREE.Vector3(scale,scale,scale)));
    }
    d.matrices=matrices;
    const high=new THREE.Group();high.name='blender_ore_clusters';high.userData.variant=keys[variant];high.userData.count=count;
    for(const part of parts){
      const cacheKey=variant+':'+d.ore+':'+part.material.name;let mat=materials.get(cacheKey);
      if(!mat){mat=part.material.clone();if(mat.name.startsWith('crystal_'))mat.color.set(d.color);if(mat.name==='crystal_emissive'){mat.emissive.set(d.color);mat.emissiveIntensity=1.8;}materials.set(cacheKey,mat);}
      const mesh=new THREE.InstancedMesh(part.geometry,mat,count);matrices.forEach((m,i)=>mesh.setMatrixAt(i,m));mesh.instanceMatrix.needsUpdate=true;mesh.computeBoundingSphere();high.add(mesh);
    }
    root.add(high);d.high=high;d.fallback.visible=false;status.active++;builds++;
  }
  return {status,load,detail,update,release,beginFrame(){builds=0;}};
})();
