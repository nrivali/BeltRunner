/* Finalize portable glTF materials and add standard KHR_materials_variants. */
const fs=require('node:fs'),path=require('node:path');
const root=__dirname;
const report=JSON.parse(fs.readFileSync(path.join(root,'asset-report.json'),'utf8'));
const variants=[...Object.keys(report.ore_types),'barren'];
const files=[];
for(let lod=0;lod<3;lod++){
  const input=fs.readFileSync(path.join(root,`asteroids_lod${lod}.raw.glb`));
  const jsonSize=input.readUInt32LE(12),j=JSON.parse(input.subarray(20,20+jsonSize));
  const bin=input.subarray(28+jsonSize);
  const retained=j.nodes.map((n,i)=>({n,i})).filter(({n})=>!n.name?.startsWith('MATERIAL_TEMPLATE_'));
  const remap=new Map(retained.map(({i},index)=>[i,index]));
  j.nodes=retained.map(({n})=>n);
  for(const scene of j.scenes)scene.nodes=scene.nodes.filter(n=>remap.has(n)).map(n=>remap.get(n));
  const usedMeshes=[...new Set(j.nodes.map(n=>n.mesh).filter(n=>n!==undefined))];
  const meshRemap=new Map(usedMeshes.map((m,i)=>[m,i]));
  j.meshes=usedMeshes.map(m=>j.meshes[m]);
  for(const n of j.nodes)if(n.mesh!==undefined)n.mesh=meshRemap.get(n.mesh);
  const stone=j.materials.findIndex(m=>m.name==='Barren_Regolith');
  const indexByOre=Object.fromEntries(variants.map(v=>[v,v==='barren'?stone:j.materials.findIndex(m=>m.name==='Ore_'+v)]));
  for(const material of j.materials){
    const p=material.pbrMetallicRoughness;
    // Blender's MixRGB texture tint is not represented by this exporter version.
    // Preserve the exact linear factors from the source Blender material extras.
    p.baseColorFactor=[...material.extras.color_factor,1];
    p.metallicFactor=material.extras.metallic_factor;
    p.roughnessFactor=material.extras.roughness_factor;
    material.doubleSided=false;
    material.emissiveFactor=[0,0,0];
    for(const info of [p.baseColorTexture,p.metallicRoughnessTexture,material.normalTexture]){
      if(info)info.texCoord=0;
    }
  }
  j.extensionsUsed=[...new Set([...(j.extensionsUsed||[]),'KHR_materials_variants'])];
  j.extensions={...(j.extensions||{}),KHR_materials_variants:{variants:variants.map(name=>({name}))}};
  for(const mesh of j.meshes)for(const primitive of mesh.primitives){
    if(primitive.material!==stone){
      primitive.extensions={...(primitive.extensions||{}),KHR_materials_variants:{mappings:variants.map((v,i)=>({material:indexByOre[v],variants:[i]}))}};
    }
  }
  j.asset.extras={...(j.asset.extras||{}),assetPack:'Belt Runner asteroid overhaul',lod,
    source:'asteroids.blend',shapeCount:14,variationsPerShape:2,emission:0,
    note:'Reset the selected node position to zero when instantiating. Colors are selectable material variants.'};
  j.scenes[j.scene||0].name=`Asteroid library / LOD ${lod}`;
  const str=Buffer.from(JSON.stringify(j)),padded=Buffer.alloc(Math.ceil(str.length/4)*4,0x20);str.copy(padded);
  const result=Buffer.alloc(28+padded.length+bin.length);
  result.writeUInt32LE(0x46546c67,0);result.writeUInt32LE(2,4);result.writeUInt32LE(result.length,8);
  result.writeUInt32LE(padded.length,12);result.writeUInt32LE(0x4e4f534a,16);padded.copy(result,20);
  result.writeUInt32LE(bin.length,20+padded.length);result.writeUInt32LE(0x004e4942,24+padded.length);bin.copy(result,28+padded.length);
  const filename=`asteroids_lod${lod}.glb`;fs.writeFileSync(path.join(root,filename),result);
  files.push({lod,file:filename,bytes:result.length,models:j.nodes.length,materials:j.materials.length,images:j.images.length});
}
fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify({formatVersion:1,source:'asteroids.blend',files,
  shapeFamilies:[...new Set(report.assets.map(a=>a.shape))],variants:['A','B'],materialVariants:variants,
  nodeName:'<shape>_<A|B>_LOD<0|1|2>',gameCoordinates:'X right, Y up, Z forward; nominal base radius 1',
  collisions:'These visual meshes do not replace the live game collision profiles. Integration must reconcile hollow/arch traversal with mesh collision.',
  lighting:'No emission or baked lighting; PBR albedo, tangent normal and roughness/metallic textures.'},null,2)+'\n');
console.log(JSON.stringify(files,null,2));
