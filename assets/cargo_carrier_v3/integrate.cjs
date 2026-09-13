const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const root=path.resolve(__dirname,'../..'),file=path.join(root,'belt-runner-3d.html'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
if(cp.execFileSync('git',['status','--porcelain','--','belt-runner-3d.html'],{cwd:root,encoding:'utf8'}).trim())throw Error('Shared game has uncommitted edits; leave it alone.');
const bytes=fs.readFileSync(file),before=sha(bytes);let s=bytes.toString('utf8');
const backup=path.join(root,'backups','rounded-carrier-'+new Date().toISOString().replace(/[:.]/g,'-')+'.html');fs.mkdirSync(path.dirname(backup),{recursive:true});fs.writeFileSync(backup,bytes);
const changes=[
 ["const GAME_VERSION = '0.9.58';","const GAME_VERSION = '0.9.59';"],
 ['<script src="assets/cargo_carrier/load-carrier.js"></script>','<script src="assets/cargo_carrier_v3/hull-contact.js"></script>\r\n<script src="assets/cargo_carrier_v3/load-carrier.js"></script>'],
 ['  if (p.x>P.x0 && p.x<P.x1){   // the prow is a cone tapering to the bow tip',
  '  if (carrierAsset.hullShape && window.BeltRunnerCarrierHull && !bayCorridor(ship.pos)){\r\n    const contact=window.BeltRunnerCarrierHull.contact(p,m,carrierAsset.hullShape);\r\n    if(contact){p.fromArray(contact.position);hit(V3(...contact.normal));}\r\n    return;\r\n  }\r\n  if (p.x>P.x0 && p.x<P.x1){   // procedural fallback prow']
];
for(const [a,b] of changes){if(s.split(a).length!==2)throw Error('Expected one anchor: '+a.slice(0,90));s=s.replace(a,b);}
if(sha(fs.readFileSync(file))!==before)throw Error('Shared game changed; reconcile latest contents before writing.');fs.writeFileSync(file,s,'utf8');
fs.writeFileSync(path.join(__dirname,'change-proof.json'),JSON.stringify({base:cp.execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),beforeSHA256:before,afterSHA256:sha(fs.readFileSync(file)),backup,changes:changes.map(([before,after])=>({before,after}))},null,2)+'\n');console.log({before,after:sha(fs.readFileSync(file)),backup});
