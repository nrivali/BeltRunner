const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
let s=fs.readFileSync(path.join(root,'tests/carrier-integration.cjs'),'utf8').replaceAll('\r\n','\n');
s=s.replace("destination=b.ZONES.find(z=>z!==b.zone&&!z.hub)","destination=b.ZONES.find(z=>z!==b.zone)");
s=s.replace('rock.pos.copy(world([2000,2400,2500]));','rock.pos.copy(world([2000,2400,2500]));rock.group.position.copy(rock.pos);rock.group.updateMatrixWorld(true);');
s=s.replace('b.updateDepot(0);b.updateVisuals(0,2);', 'for(let i=0;i<10;i++){const aim=rock.asset?b.rockAssets.aimPoint(rock,b.turretMuzzleWorld(b.depotLaser.yaw,b.depotLaser.pitch)):rock.pos;Object.assign(b.depotLaser,b.turretAnglesTo(aim));b.updateDepot(0);}b.updateVisuals(0,2);');
s=s.replace('rock.pos.copy(saved.pos);rock.hp=', 'rock.pos.copy(saved.pos);rock.group.position.copy(saved.pos);rock.hp=');
s=s.replace('for(let i=0;i<220;i++)b.update(.05);','for(let i=0;i<1000;i++){b.update(.05);if(i>=200&&b.zone===destination&&b.flags.docked&&!b.cut)break;}');
s=s.replace("if(b.zone!==destination||!b.flags.docked||model.uuid!==id||model.parent!==b.station)", "if(b.zone!==destination||!b.flags.docked||b.cut||model.uuid!==id||model.parent!==b.station)");
s=s.replace('normalMaps:a.materials', 'baseColorSize:a.materials&&Object.values(a.materials)[0].map.image.width,hullStations:a.hullShape?.stations.length,normalMaps:a.materials');
s=s.replace('assert.ok(result.normalMaps);', 'assert.ok(result.normalMaps);assert.equal(result.baseColorSize,4096);assert.equal(result.hullStations,18);');
s=s.replace('results.push({mode,...result,pageErrors:errors});', "results.push({mode,...result,pageErrors:errors});console.log('PASS '+mode);");
s=s.replaceAll('cargo_carrier_v2','cargo_carrier_v3').replace('result.revision,2','result.revision,3').replace('result.triangles,35316','result.triangles,28876').replace('result.totalTriangles,37496','result.totalTriangles,31056')
 .replace('[[-3580,0,-540],[-3580,0,0],[-3580,0,540]]','[[-3580,220,0],[-3580,-140,-470],[-3580,-140,470]]')
 .replace("path.join(__dirname,'carrier-results.json')","path.join(root,'assets/cargo_carrier_v3/integration-validation.json')")
 .replace("const results=[];","const results=[];const crypto=require('node:crypto'),gameFile=path.join(root,'belt-runner-3d.html'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),gameSHA=sha(fs.readFileSync(gameFile));")
 .replace('JSON.stringify(results,null,2));console.log',"JSON.stringify({gameSHA256:gameSHA,assetSHA256:sha(fs.readFileSync(path.join(root,'assets/cargo_carrier_v3/cargo_carrier_assembled.glb'))),results},null,2));assert.equal(sha(fs.readFileSync(gameFile)),gameSHA,'Shared game changed during testing');console.log")
 .replaceAll('b.renderer.render(b.scene,b.camera);','b.lighting.update({camera:b.camera,station:b.station,quality:\'balanced\',dt:.1});b.renderer.render(b.scene,b.camera);');
fs.writeFileSync(path.join(root,'tests/cargo-carrier-v3-integration.cjs'),s);
