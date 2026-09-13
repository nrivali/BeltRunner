const fs=require('node:fs'),path=require('node:path');
const bytes=fs.readFileSync(path.join(__dirname,'garden-habitat.glb'));
fs.writeFileSync(path.join(__dirname,'garden-habitat.data.js'),'window.BeltRunnerGardenColonyData="'+bytes.toString('base64')+'";\n');
console.log('Garden Habitat GLB bytes:',bytes.length);
