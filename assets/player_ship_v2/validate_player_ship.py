import bpy, json, struct, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
raw=(P/'player_ship.glb').read_bytes();magic,version,total=struct.unpack_from('<III',raw)
assert (magic,version,total)==(0x46546c67,2,len(raw))
n,kind=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+n]);binary=raw[28+n:]
assert len(doc['scenes'])==2 and doc['scene']==0
assert not doc.get('cameras') and not doc.get('extensions',{}).get('KHR_lights_punctual')
required=['hull','wings_delta','wings_swept','wings_forward','wings_twin','dish_mount','engine_l','engine_r','nav_l','nav_r']+[f'{p}_{i}' for p in ('laser_barrel','cargo_pod','engine_nacelle','scanner_dish') for i in (1,2,3)]
nodes={o['name']:o for o in doc['nodes']}
assert all(k in nodes for k in required)
assert all(abs(a-b)<1e-5 for a,b in zip(nodes['dish_mount']['translation'],[0,-3.4,7]))
assert {m['name'] for m in doc['materials']}=={'paint','trim','glass','emissive'}
assert len(doc['images'])==4
for im in doc['images']:
    view=doc['bufferViews'][im['bufferView']];offset=view.get('byteOffset',0)
    assert binary[offset:offset+8]==b'\x89PNG\r\n\x1a\n'
    assert struct.unpack_from('>II',binary,offset+16)in [(4096,4096),(2048,2048)]

def accessor(i):
    a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']];fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']];size={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    stride=v.get('byteStride',struct.calcsize(fmt)*size);offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    return [struct.unpack_from('<'+fmt*size,binary,offset+k*stride) for k in range(a['count'])]
tris=[]
for m in doc['meshes']:
    for pr in m['primitives']:
        assert pr.get('mode',4)==4;assert 'TEXCOORD_0' in pr['attributes'] and 'TEXCOORD_1' not in pr['attributes']
        uv=accessor(pr['attributes']['TEXCOORD_0']);ids=[v[0] for v in accessor(pr['indices'])]
        assert all(-1e-5<=c<=1.00001 for pair in uv for c in pair)
        for k in range(0,len(ids),3):
            t=[uv[ids[k+i]] for i in range(3)]
            area=abs((t[1][0]-t[0][0])*(t[2][1]-t[0][1])-(t[1][1]-t[0][1])*(t[2][0]-t[0][0]))
            if area>1e-10:tris.append(t)
# Positive-area triangle intersection test in the UV atlas (shared edges are allowed).
def overlap(a,b):
    for tri in (a,b):
        for i in range(3):
            p,q=tri[i],tri[(i+1)%3];axis=(p[1]-q[1],q[0]-p[0]);length=math.hypot(*axis)
            if length<1e-10:continue
            aa=[(v[0]*axis[0]+v[1]*axis[1])/length for v in a];bb=[(v[0]*axis[0]+v[1]*axis[1])/length for v in b]
            if min(max(aa),max(bb))-max(min(aa),min(bb))<=2e-7:return False
    return True
cells={};tested=set();collisions=[]
for i,t in enumerate(tris):
    xmin,xmax=min(v[0] for v in t),max(v[0] for v in t);ymin,ymax=min(v[1] for v in t),max(v[1] for v in t)
    for x in range(int(xmin*32),int(xmax*32)+1):
        for y in range(int(ymin*32),int(ymax*32)+1):
            cell=cells.setdefault((x,y),[])
            for j in cell:
                if (i,j) in tested:continue
                tested.add((i,j))
                if overlap(t,tris[j]):collisions.append((i,j))
            cell.append(i)
assert not collisions, f'Overlapping UV triangles: {collisions[:10]}'

bpy.ops.wm.open_mainfile(filepath=str(P/'player_ship.blend'))
scene=bpy.context.scene;report=json.loads((P/'asset_report.json').read_text())
assert max(report['assembled_triangle_counts'].values())<=24000
for o in scene.objects:
    if o.type=='MESH':assert all(abs(s-1)<1e-6 for s in o.scale)
allpts=[o.matrix_world@v.co for o in scene.objects if o.type=='MESH' for v in o.data.vertices]
radius=max(v.length for v in allpts);assert radius<=16
def tree(objects):
    vertices=[];faces=[]
    for o in objects:
        start=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices);faces.extend(tuple(start+i for i in p.vertices) for p in o.data.polygons)
    return BVHTree.FromPolygons(vertices,faces,all_triangles=True)
static_names=['hull','hull_trim','canopy','cockpit','cockpit_frame','engine_core','emissive','engine_nacelle_3','cargo_pod_3','scanner_dish_3']
static=tree([bpy.data.objects[n] for n in static_names]);yaw=bpy.data.objects['mining_dish_yaw'];pitch=bpy.data.objects['mining_dish_pitch']
sweeps=0
for level in (1,2,3):
    barrel=bpy.data.objects[f'laser_barrel_{level}'];saved_parent=barrel.parent;world=barrel.matrix_world.copy();barrel.parent=pitch;barrel.matrix_world=world
    for degrees in range(-90,91,5):
        for elevation in [-.7,-.35,0,.65,1.3]:
            yaw.rotation_euler.z=math.radians(degrees);pitch.rotation_euler.x=elevation;bpy.context.view_layer.update()
            moving=tree([bpy.data.objects['mining_dish'],bpy.data.objects['dish_yoke'],barrel])
            assert not static.overlap(moving), f'Chin sweep intersects hull: level {level}, yaw {degrees}, pitch {elevation}'
            sweeps+=1
    yaw.rotation_euler.z=0;pitch.rotation_euler.x=0;bpy.context.view_layer.update();barrel.parent=saved_parent;barrel.matrix_world=world;bpy.context.view_layer.update()
result={'status':'PASS','required_nodes':len(required),'assembled_triangle_range':[min(report['assembled_triangle_counts'].values()),max(report['assembled_triangle_counts'].values())],'all_components_triangles':report['triangles_all_components'],'radius':radius,'texture_sizes':report['map_sizes'],'embedded_pngs':4,'uv_overlap_count':len(collisions),'yaw_clearance_samples':sweeps,'yaw_range_degrees':[-90,90],'pitch_range_radians':[-.7,1.3],'camera_or_lights_in_glb':False,'scene_count':2}
(P/'validation.json').write_text(json.dumps(result,indent=2));print('VALIDATION',json.dumps(result))
