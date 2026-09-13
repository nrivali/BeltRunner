const fs=require('node:fs'),path=require('node:path');
const keys=['01_needle','02_fan','03_crown','04_split_spire','05_ridge','06_bloom'];
const data=keys.map(k=>fs.readFileSync(path.join(__dirname,k,`ore_cluster_${k}.glb`)).toString('base64'));
fs.writeFileSync(path.join(__dirname,'ore_clusters.data.js'),'// Generated GLB payloads for direct file:// play.\nwindow.BeltRunnerOreData='+JSON.stringify(data)+';\n');
