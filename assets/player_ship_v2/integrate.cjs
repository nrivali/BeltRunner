// Apply only the two player-asset URLs and one version increment to a clean game.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..'),file=path.join(root,'belt-runner-3d.html'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const git=args=>cp.execFileSync('git',args,{cwd:root,encoding:'utf8'}).trim();
if(git(['status','--porcelain','--','belt-runner-3d.html']))throw Error('Other uncommitted game changes; wait for the shared commit.');
const base=git(['rev-parse','HEAD']),bytes=fs.readFileSync(file),before=sha(bytes);let s=bytes.toString('utf8');
const version=s.match(/const GAME_VERSION = '(\d+)\.(\d+)\.(\d+)';/);if(!version)throw Error('Version missing');
const changes=[[version[0],`const GAME_VERSION = '${version[1]}.${version[2]}.${Number(version[3])+1}';`],['<script src="assets/player_ship/assemble-player-ship.global.js"></script>','<script src="assets/player_ship_v2/assemble-player-ship.global.js"></script>'],['<script src="assets/player_ship/load-player-ship.js"></script>','<script src="assets/player_ship_v2/load-player-ship.js"></script>']];
for(const [a,b] of changes){if(s.split(a).length!==2)throw Error('Changed integration anchor: '+a);s=s.replace(a,b);}
const backup=path.join(root,'backups','rounded-player-'+new Date().toISOString().replace(/[:.]/g,'-')+'.html');fs.writeFileSync(backup,bytes);
if(sha(fs.readFileSync(file))!==before||git(['rev-parse','HEAD'])!==base)throw Error('Shared file changed; reconcile latest source');fs.writeFileSync(file,s,'utf8');
const proof={base,beforeSHA256:before,afterSHA256:sha(fs.readFileSync(file)),backup,changes:changes.map(([before,after])=>({before,after}))};fs.writeFileSync(path.join(__dirname,'change-proof.json'),JSON.stringify(proof,null,2)+'\n');console.log(proof);
