import bpy, math, json, struct
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'player_ship.blend'))
scene=bpy.context.scene;cam=scene.camera;original=cam.matrix_world.copy();oldscale=cam.data.ortho_scale
names=json.loads((P/'asset_report.json').read_text())['triangles_by_mesh']
def configure(wing):
    for name in names:
        o=bpy.data.objects[name]
        visible=(not name.startswith(('wings_','laser_barrel_','cargo_pod_','engine_nacelle_','scanner_dish_')) or name=='wings_'+wing or name in [f'{p}_1' for p in ('laser_barrel','cargo_pod','engine_nacelle','scanner_dish')])
        o.hide_render=not visible;o.hide_set(not visible)
cam.location=(0,0,42);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=40;scene.cycles.samples=48
for wing in ('delta','swept','forward','twin'):
    configure(wing);scene.render.filepath=str(P/f'wings_{wing}.png');bpy.ops.render.render(write_still=True)
configure('delta');cam.matrix_world=original;cam.data.ortho_scale=oldscale;scene.cycles.samples=96
# Focus marks the glowing front face of the default emitter barrel.
bpy.data.objects['focus'].location.y=-2.17
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'player_ship.blend'))
raw=(P/'player_ship.glb').read_bytes();n,_=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+n]);tail=raw[20+n:]
for node in doc['nodes']:
    if node['name']=='focus':node['translation']=[0,0,2.17]
payload=json.dumps(doc,separators=(',',':')).encode();payload+=b' '*((-len(payload))%4)
(P/'player_ship.glb').write_bytes(struct.pack('<III',0x46546c67,2,20+len(payload)+len(tail))+struct.pack('<II',len(payload),0x4e4f534a)+payload+tail)
