const fs=require('node:fs'),path=require('node:path');
const bytes=fs.readFileSync(path.join(__dirname,'homeworld.glb'));
fs.writeFileSync(path.join(__dirname,'homeworld.data.js'),'window.BeltRunnerHomeworldData="'+bytes.toString('base64')+'";\n');
console.log('Homeworld GLB bytes:',bytes.length);
