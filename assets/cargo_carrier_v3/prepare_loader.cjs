const fs=require('node:fs'),path=require('node:path');
let s=fs.readFileSync(path.join(__dirname,'../cargo_carrier/load-carrier.js'),'utf8').replaceAll('\r\n','\n');
s=s.replace('assets/cargo_carrier_v2/','assets/cargo_carrier_v3/').replace('triangles+dishTriangles>40000','triangles+dishTriangles>65000').replace('revision:2','revision:3');
const anchor="    const yaw=model.getObjectByName('dish_yaw'),nativePitch=model.getObjectByName('dish_pitch');";
if(!s.includes(anchor))throw Error('Loader anchor missing');
s=s.replace(anchor,"    const hullShape=JSON.parse(model.getObjectByName('hull_collision_profile')?.userData.definition||'null');\n    if(!hullShape||!Array.isArray(hullShape.stations)||hullShape.stations.length<3||!Number.isFinite(hullShape.exponent))throw Error('Missing curved hull profile');\n"+anchor);
s=s.replace('totalTriangles:triangles+dishTriangles,anchors,materials,error:null','totalTriangles:triangles+dishTriangles,anchors,materials,hullShape,error:null');
fs.writeFileSync(path.join(__dirname,'load-carrier.js'),s);
