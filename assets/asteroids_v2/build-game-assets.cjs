// Convert the approved Blender GLBs to a shared, compressed runtime library.
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
const out=__dirname,report=JSON.parse(fs.readFileSync(path.join(out,'asset-report.json')));
const chunks=[],header={version:2,models:[],textures:{},ores:report.ore_types};let offset=0;
function append(data){const b=Buffer.from(data.buffer,data.byteOffset,data.byteLength);const view={offset,length:b.length};chunks.push(b);offset+=b.length;const padding=(4-offset%4)%4;if(padding){chunks.push(Buffer.alloc(padding));offset+=padding;}return view;}
const sizeOf={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4},widthOf={SCALAR:1,VEC2:2,VEC3:3,VEC4:4};
for(let lod=0;lod<3;lod++){
 const file=fs.readFileSync(path.join(out,`asteroids_lod${lod}.glb`)),n=file.readUInt32LE(12),j=JSON.parse(file.subarray(20,20+n)),bin=file.subarray(28+n);
 function read(index){const a=j.accessors[index],v=j.bufferViews[a.bufferView],width=widthOf[a.type],bytes=sizeOf[a.componentType],result=[];
  const getters={5120:'readInt8',5121:'readUInt8',5122:'readInt16LE',5123:'readUInt16LE',5125:'readUInt32LE',5126:'readFloatLE'};
  for(let i=0;i<a.count;i++)for(let c=0;c<width;c++)result.push(bin[getters[a.componentType]]((v.byteOffset||0)+(a.byteOffset||0)+i*(v.byteStride||width*bytes)+c*bytes));return result;
 }
 for(const node of j.nodes){if(node.mesh===undefined)continue;const mesh=j.meshes[node.mesh],p=[],normal=[],tangent=[],uv=[],mask=[],indices=[];
  for(const primitive of mesh.primitives){const start=p.length/3,pp=read(primitive.attributes.POSITION);p.push(...pp);normal.push(...read(primitive.attributes.NORMAL));tangent.push(...read(primitive.attributes.TANGENT));uv.push(...read(primitive.attributes.TEXCOORD_0));
   const ore=j.materials[primitive.material].name.startsWith('Ore_');for(let i=0;i<pp.length/3;i++)mask.push(ore?1:0);for(const i of read(primitive.indices))indices.push(start+i);
  }
  const key=node.name.replace(/_LOD\d$/,''),count=p.length/3,Index=count<65536?Uint16Array:Uint32Array;
  const attrs={position:append(new Float32Array(p)),normal:append(new Int16Array(normal.map(v=>Math.round(v*32767)))),tangent:append(new Int16Array(tangent.map(v=>Math.round(v*32767)))),uv:append(new Float32Array(uv)),ore:append(new Uint8Array(mask)),index:append(new Index(indices))};
  header.models.push({key,lod,count,indexType:Index===Uint16Array?16:32,attributes:attrs});
 }
}
for(const kind of ['regolith','ore'])for(const channel of ['albedo','normal','metalrough']){const name=`${kind}_${channel}`;header.textures[name]=append(fs.readFileSync(path.join(out,'textures',name+'.png')));}
const json=Buffer.from(JSON.stringify(header)),pad=Buffer.alloc(Math.ceil(json.length/4)*4,32);json.copy(pad);const prefix=Buffer.alloc(12);prefix.write('BRR2');prefix.writeUInt32LE(pad.length,4);prefix.writeUInt32LE(offset,8);
const raw=Buffer.concat([prefix,pad,...chunks]),compressed=zlib.gzipSync(raw,{level:9});
fs.writeFileSync(path.join(out,'asteroids-game.bin.gz'),compressed);
fs.writeFileSync(path.join(out,'asteroids-game.data.js'),'window.BeltRunnerAsteroidData='+JSON.stringify(compressed.toString('base64'))+';\n');
const result={models:header.models.length,textures:Object.keys(header.textures).length,rawBytes:raw.length,gzipBytes:compressed.length,drawCallsPerBatch:1,source:'Approved Blender GLBs',normalTangentQuantization:16};
fs.writeFileSync(path.join(out,'game-build.json'),JSON.stringify(result,null,2)+'\n');console.log(result);
