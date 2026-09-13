// A guarded, narrow edit against the current shared game file, with a pre-edit backup.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),file=path.join(root,'belt-runner-3d.html'),bytes=fs.readFileSync(file);
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const expected='9544bd39f8ead6bfb2a82f5315c1c7b6eb31f472d66581a0fe494940f00570f8';
if(hash(bytes)!==expected)throw Error('Game changed: reread and reconcile before editing.');
const nl=bytes.includes(Buffer.from('\r\n'))?'\r\n':'\n';let text=bytes.toString('utf8');
function after(anchor,line){if(text.split(anchor).length!==2)throw Error('Anchor missing or ambiguous');text=text.replace(anchor,anchor+nl+line);}
after('<script src="assets/ore_clusters/load-ore-clusters.js"></script>','<script src="assets/asteroid_surface/load-rock-texture.js"></script>');
after("  mat.customProgramCacheKey=()=>'heat';",'  window.BeltRunnerRockSurface?.apply(mat);');
after('if(window.BeltRunnerOreClusters)BeltRunnerOreClusters.load(renderer);','if(window.BeltRunnerRockSurface)BeltRunnerRockSurface.load({renderer,baseMaterials:[rockMat,rockMatSmooth,rockMatCave,barrenMat],oreMaterials:oreRockMats,ores:ORES,veinMask,veinSize:VEIN_N,asteroids:()=>asteroids,heatable});');
const folder=path.join(root,'backups');fs.mkdirSync(folder,{recursive:true});const backup=path.join(folder,'belt-runner-3d.before-rock-textures.'+new Date().toISOString().replace(/[:.]/g,'-')+'.html');fs.writeFileSync(backup,bytes,{flag:'wx'});
if(hash(fs.readFileSync(file))!==expected)throw Error('Game changed before write; no edit applied.');
fs.writeFileSync(file,text);console.log(JSON.stringify({backup,before:expected,after:hash(Buffer.from(text)),addedLines:3}));
