const fs=require('node:fs'),path=require('node:path');
let data=fs.readFileSync(path.join(__dirname,'planet.glb'));
const jsonSize=data.readUInt32LE(12),j=JSON.parse(data.subarray(20,20+jsonSize));
if(!j.materials.some(m=>m.name==='Planet_Detail')){
  const chunks=[data.subarray(28+jsonSize)];let length=chunks[0].length;
  j.samplers=j.samplers||[];const sampler=j.samplers.push({magFilter:9729,minFilter:9987,wrapS:10497,wrapT:10497})-1;
  const add=name=>{
    const bytes=fs.readFileSync(path.join(__dirname,'../asteroids_v2/textures',name)),pad=Buffer.alloc((4-bytes.length%4)%4);
    const view=j.bufferViews.push({buffer:0,byteOffset:length,byteLength:bytes.length})-1;
    chunks.push(bytes,pad);length+=bytes.length+pad.length;
    const source=j.images.push({name,bufferView:view,mimeType:'image/png'})-1;
    return j.textures.push({sampler,source})-1;
  };
  const color=add('regolith_albedo.png'),normal=add('regolith_normal.png');
  j.materials.push({name:'Planet_Detail',pbrMetallicRoughness:{baseColorTexture:{index:color},roughnessFactor:1,metallicFactor:0},normalTexture:{index:normal}});
  j.asset.extras={...(j.asset.extras||{}),detailMaterial:'Planet_Detail',detailSource:'ImageGen-derived Blender regolith maps from the existing asteroid pack',detailUVScale:36};
  j.buffers[0].byteLength=length;
  const json=Buffer.from(JSON.stringify(j)),padded=Buffer.alloc(Math.ceil(json.length/4)*4,0x20);json.copy(padded);
  data=Buffer.alloc(28+padded.length+length);data.writeUInt32LE(0x46546c67,0);data.writeUInt32LE(2,4);data.writeUInt32LE(data.length,8);
  data.writeUInt32LE(padded.length,12);data.writeUInt32LE(0x4e4f534a,16);padded.copy(data,20);
  data.writeUInt32LE(length,20+padded.length);data.writeUInt32LE(0x004e4942,24+padded.length);Buffer.concat(chunks).copy(data,28+padded.length);
  fs.writeFileSync(path.join(__dirname,'planet.glb'),data);
}
fs.writeFileSync(path.join(__dirname,'planet.data.js'),'window.BeltRunnerPlanetData="'+data.toString('base64')+'";\n');
console.log('Planet GLB bytes:',data.length);
