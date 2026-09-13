// Generate a standalone builder from the proven interior/rig pipeline and the new curved exterior.
const fs=require('node:fs'),path=require('node:path');
const dir=__dirname,base=fs.readFileSync(path.join(dir,'../cargo_carrier_v2/build_carrier.py'),'utf8').replaceAll('\r\n','\n');
const between=(a,b)=>{const x=base.indexOf(a),y=b?base.indexOf(b,x):base.length;if(x<0||y<x)throw Error('Builder marker missing');return base.slice(x,y);};
let source=base.slice(0,base.indexOf('# Beveled pressure hull'))+'\n'+fs.readFileSync(path.join(dir,'hull_geometry.py'),'utf8')+'\n'+between('# Fully modeled hangar','# Raised bridge')+between('# The off-flank','# Separate articulated dish')+between('# Separate articulated dish');
source=source.replace("'light':'B4BCCF','mid':'9AA4BF','plate':'828CA9','dark':'303847','structure':'566078'","'light':'E9E3D2','mid':'CFCABA','plate':'89969C','dark':'242C34','structure':'667680'")
 .replace("mat['metalness']=.28 if k not in EMIT else .2;mat['roughness']=.72 if k=='dark' else .48","mat['metalness']=.64 if k in ('dark','structure') else .34;mat['roughness']=.56 if k=='dark' else .37")
 .replace("tint.inputs[0].default_value=.45","tint.inputs[0].default_value=.8")
 .replace("box('ceiling skin',(0,183,0),(840,14,1800),'dark','interior',0)","# The liner underside is at 170, six units below the hull's 176 ceiling face.\n# Coplanar surfaces here flicker against each other as the hangar camera moves.\nbox('ceiling skin',(0,177,0),(840,14,1800),'dark','interior',0)")
 .replace("'engine_0':(-3480,0,-540),'engine_1':(-3480,0,0),'engine_2':(-3480,0,540)","'engine_0':(-3480,220,0),'engine_1':(-3480,-140,-470),'engine_2':(-3480,-140,470)")
 .replace("'bridge_windows':(900,734,0)","'bridge_windows':(2200,610,0)")
 .replace("anchors={n:empty(n,p) for n,p in ANCHORS.items()}","anchors={n:empty(n,p) for n,p in ANCHORS.items()}\nshape=empty('hull_collision_profile',(0,0,0));shape['definition']=json.dumps({'stations':PROFILE,'exponent':EXPONENT,'engines':[[-3550,-2840,y,z,283] for y,z in ENGINE_CENTERS]})")
 .replace('width=2048,height=2048','width=4096 if kind==\'basecolor\' else 2048,height=4096 if kind==\'basecolor\' else 2048')
 .replace('<=40000,counts','<=65000,counts')
 .replace('carrier+list(anchors.values()))','carrier+list(anchors.values())+[shape])')
 .replace("carrier+list(anchors.values())+[objects['dish_yaw']", "carrier+list(anchors.values())+[shape,objects['dish_yaw']")
 .replace("'atlas_size':2048", "'atlas_size':4096,'map_sizes':{k:list(im.size) for k,im in maps.items()},'profile':PROFILE,'exponent':EXPONENT")
 .replace('scene.render.resolution_x=2000;scene.render.resolution_y=1125','scene.render.resolution_x=1800;scene.render.resolution_y=1100')
 .replace('scene.cycles.samples=96','scene.cycles.samples=48')
 .replace("for z in (-540,0,540):area('Engine bounce',(-3555,0,z),1e6,240,(.2,.7,1),(-4300,0,z))","for y,z in ENGINE_CENTERS:area('Engine bounce',(-3555,y,z),1e6,240,(.2,.7,1),(-4300,y,z))")
 .replace('CARRIER_V2_COMPLETE','CARRIER_V3_COMPLETE');
fs.writeFileSync(path.join(dir,'build_carrier.py'),source);
console.log('Standalone curved carrier builder written');
