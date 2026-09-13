import bpy, json, struct
from pathlib import Path
from mathutils import Vector
p=Path(__file__).resolve().parent
raw=(p/'cargo_carrier.glb').read_bytes()
magic,version,length=struct.unpack_from('<III',raw)
assert magic==0x46546c67 and version==2 and length==len(raw)
n,t=struct.unpack_from('<II',raw,12); doc=json.loads(raw[20:20+n])
assert not doc.get('cameras')
assert 'KHR_lights_punctual' not in doc.get('extensions',{})
assert all('bufferView' in im for im in doc['images'])
tris=sum(doc['accessors'][pr['indices']]['count']//3 for m in doc['meshes'] for pr in m['primitives'])
assert tris<=40000
report=json.loads((p/'asset_report.json').read_text())
nodes={node['name']:node for node in doc['nodes']}
for name,expected in report['empties'].items():
    actual=nodes[name].get('translation',[0,0,0]); assert all(abs(a-b)<.01 for a,b in zip(expected,actual)),(name,actual,expected)
assert len(doc['materials'])==4
for m in doc['meshes']:
    for pr in m['primitives']:assert 'TEXCOORD_0' in pr['attributes'] and 'TEXCOORD_1' not in pr['attributes']
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(p/'cargo_carrier.glb'))
deps=bpy.context.evaluated_depsgraph_get()
# Free central flight path across the tunnel: game z maps to Blender -y.
hit=bpy.context.scene.ray_cast(deps,Vector((0,-1100,0)),Vector((0,1,0)),distance=2200)[0]
assert not hit, 'Through hangar is obstructed'
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
assert len(meshes)==4
for o in meshes:assert all(abs(s-1)<1e-6 for s in o.scale)
result={'status':'PASS','triangles':tris,'materials':len(doc['materials']),'embedded_images':len(doc['images']),'attachment_points_checked':len(report['empties']),'through_hangar_raycast':'clear','camera_and_lights_in_glb':False}
(p/'validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
