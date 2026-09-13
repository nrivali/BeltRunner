// Narrow, hash-guarded integration into the current shared game; never restores a snapshot.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const root=path.resolve(__dirname,'../..'),file=path.join(root,'belt-runner-3d.html');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
if(cp.execFileSync('git',['status','--porcelain','--','belt-runner-3d.html'],{cwd:root,encoding:'utf8'}).trim())throw Error('Shared game has uncommitted changes. Leave it alone.');
const bytes=fs.readFileSync(file),before=sha(bytes);let source=bytes.toString('utf8');
const backup=path.join(root,'backups','garden-colony-'+new Date().toISOString().replace(/[:.]/g,'-')+'.html');fs.mkdirSync(path.dirname(backup),{recursive:true});fs.writeFileSync(backup,bytes);
const changes=[
 ["const GAME_VERSION = '0.9.56';","const GAME_VERSION = '0.9.57';"],
 ['<script src="assets/hub_planet/load-homeworld.js"></script>','<script src="assets/hub_planet/load-homeworld.js"></script>\r\n<script src="assets/colony_garden/load-colony.js"></script>'],
 ['  return {group:g, ring, beacons:beaconGroups, dish, pos:g.position, site, name:site.name, scale:site.scale, rot:site.rot, r:Ro*site.scale, main:!!site.main};',
  '  const c={group:g, ring, beacons:beaconGroups, dish, pos:g.position, site, name:site.name, scale:site.scale, rot:site.rot, r:Ro*site.scale, main:!!site.main};\r\n  if(window.BeltRunnerGardenColony)window.BeltRunnerGardenColony.attach(c,{renderer}).then(()=>{if(colony===c)colony_dish=c.dish;});\r\n  return c;'],
 ['  for (const c of colonies){ scene.remove(c.group); c.group.traverse(o=>{ if (o.geometry) o.geometry.dispose(); }); }',
  '  for (const c of colonies){ window.BeltRunnerGardenColony?.release(c); scene.remove(c.group); c.group.traverse(o=>{ if (o.geometry && !o.userData.gardenShared) o.geometry.dispose(); }); }'],
 ['    c.ring.rotation.y+=0.01*dt*(c.main?1:1.6); c.dish.rotation.y=t*0.08+c.rot;',
  '    c.ring.rotation.y+=0.01*dt*(c.main?1:1.6); c.dish.rotation.y=t*0.08+c.rot; window.BeltRunnerGardenColony?.update(c,t);']
];
for(const [old,next] of changes){if(source.split(old).length!==2)throw Error('Expected one integration anchor: '+old.slice(0,90));source=source.replace(old,next);}
if(sha(fs.readFileSync(file))!==before)throw Error('Shared game changed during preparation. Reconcile latest contents.');
fs.writeFileSync(file,source,'utf8');
fs.writeFileSync(path.join(__dirname,'change-proof.json'),JSON.stringify({base:cp.execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),beforeSHA256:before,afterSHA256:sha(fs.readFileSync(file)),backup,changes:changes.map(([before,after])=>({before,after}))},null,2)+'\n');
console.log({before,after:sha(fs.readFileSync(file)),backup});
