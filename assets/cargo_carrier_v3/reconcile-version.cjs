// Reconcile our two known game edits over the latest committed shared game.
// Refuse all unrelated uncommitted changes; never replace the game from HEAD.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..'),file=path.join(root,'belt-runner-3d.html');
const git=args=>cp.execFileSync('git',args,{cwd:root}),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const base=git(['rev-parse','HEAD']).toString().trim(),head=git(['show','HEAD:belt-runner-3d.html']).toString('utf8');
const bytes=fs.readFileSync(file),current=bytes.toString('utf8'),before=sha(bytes),proof=JSON.parse(fs.readFileSync(path.join(__dirname,'change-proof.json')));
const version=/const GAME_VERSION = '(\d+)\.(\d+)\.(\d+)';/;
const v=head.match(version);if(!v)throw Error('Missing version');
let expected=head;
for(const change of proof.changes.filter(c=>!c.before.includes('GAME_VERSION'))){if(expected.split(change.before).length!==2)throw Error('Integration anchor changed');expected=expected.replace(change.before,change.after);}
if(expected.replace(version,'VERSION')!==current.replace(version,'VERSION'))throw Error('Unrelated uncommitted game changes; leave them alone.');
if(git(['diff','--cached','--name-only']).toString().trim())throw Error('Other staged work; leave index alone.');
const next=`const GAME_VERSION = '${v[1]}.${v[2]}.${Number(v[3])+1}';`,updated=current.replace(version,next);
const backup=path.join(root,'backups','rounded-carrier-reconcile-'+new Date().toISOString().replace(/[:.]/g,'-')+'.html');fs.writeFileSync(backup,bytes);
if(sha(fs.readFileSync(file))!==before||git(['rev-parse','HEAD']).toString().trim()!==base)throw Error('Shared state changed before write');
fs.writeFileSync(file,updated,'utf8');
proof.reconciliations??=[];proof.reconciliations.push({base,beforeSHA256:before,afterSHA256:sha(Buffer.from(updated)),backup,version:next});
fs.writeFileSync(path.join(__dirname,'change-proof.json'),JSON.stringify(proof,null,2)+'\n');console.log(proof.reconciliations.at(-1));
