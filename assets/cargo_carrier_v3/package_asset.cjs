const fs=require('node:fs'),path=require('node:path');
const b=fs.readFileSync(path.join(__dirname,'cargo_carrier_assembled.glb'));
fs.writeFileSync(path.join(__dirname,'cargo_carrier_assembled.data.js'),'window.BeltRunnerCarrierData="'+b.toString('base64')+'";\n');
console.log('Rounded carrier GLB bytes:',b.length);
