import bpy,json,struct,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
report=json.loads((ROOT/'asset_report.json').read_text())
def readglb(name):
    raw=(ROOT/name).read_bytes();assert struct.unpack_from('<III',raw)==(0x46546c67,2,len(raw));n,t=struct.unpack_from('<II',raw,12);return json.loads(raw[20:20+n]),raw[28+n:]
doc,binary=readglb('cargo_carrier.glb')
assert len(doc['meshes'])==4 and len(doc['materials'])==4
assert {m['name'] for m in doc['meshes']}=={'hull','interior','emissive','glass'}
assert not doc.get('cameras') and not doc.get('extensions',{}).get('KHR_lights_punctual')
nodes={o['name']:o for o in doc['nodes']}
for name,p in report['empties'].items():assert all(abs(a-b)<.01 for a,b in zip(nodes[name].get('translation',[0,0,0]),p)),name
assert len(doc['images'])==4
for im in doc['images']:
    view=doc['bufferViews'][im['bufferView']];o=view.get('byteOffset',0);assert binary[o:o+8]==b'\x89PNG\r\n\x1a\n';assert struct.unpack_from('>II',binary,o+16)==(2048,2048)
for mat in doc['materials']:assert 'normalTexture' in mat and 'metallicRoughnessTexture' in mat['pbrMetallicRoughness']
def accessor(i):
    a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']];fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']];size={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    stride=v.get('byteStride',struct.calcsize(fmt)*size);offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    return [struct.unpack_from('<'+fmt*size,binary,offset+k*stride) for k in range(a['count'])]
count=0;tris=[];xs=[]
for me in doc['meshes']:
    for pr in me['primitives']:
        at=pr['attributes'];assert 'TEXCOORD_0' in at and 'TEXCOORD_1' not in at;uv=accessor(at['TEXCOORD_0']);idx=[v[0] for v in accessor(pr['indices'])];count+=len(idx)//3
        xs.extend(v[0] for v in accessor(at['POSITION']));assert all(-1e-6<=v<=1.000001 for pair in uv for v in pair)
        for k in range(0,len(idx),3):
            tri=[uv[idx[k+j]] for j in range(3)];a,b,c=tri;area=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
            if area>1e-10:tris.append(tri)
assert count==report['triangles'] and count<40000
assert abs(min(xs)+3550)<.05 and abs(max(xs)-4600)<.05,(min(xs),max(xs))
def overlap(a,b):
    for tri in (a,b):
        for i in range(3):
            p,q=tri[i],tri[(i+1)%3];axis=(p[1]-q[1],q[0]-p[0]);length=math.hypot(*axis)
            if length<1e-10:continue
            aa=[(v[0]*axis[0]+v[1]*axis[1])/length for v in a];bb=[(v[0]*axis[0]+v[1]*axis[1])/length for v in b]
            if min(max(aa),max(bb))-max(min(aa),min(bb))<=3e-7:return False
    return True
cells={};tested=set();collisions=[]
for i,t in enumerate(tris):
    for x in range(int(min(v[0] for v in t)*128),int(max(v[0] for v in t)*128)+1):
        for y in range(int(min(v[1] for v in t)*128),int(max(v[1] for v in t)*128)+1):
            cell=cells.setdefault((x,y),[])
            for j in cell:
                if (i,j) in tested:continue
                tested.add((i,j))
                if overlap(t,tris[j]):collisions.append((i,j))
            cell.append(i)
assert not collisions,f'UV overlaps: {collisions[:10]}'
print('UV_CHECK_PASS',len(tris),flush=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'cargo_carrier.glb'));deps=bpy.context.evaluated_depsgraph_get();rays=0
for x in (-330,-220,-110,0,110,220,330):
    for y in (-100,-50,0,50,90):
        for direction in (-1,1):
            hit=bpy.context.scene.ray_cast(deps,Vector((x,direction*1100,y)),Vector((0,-direction,0)),distance=2200)[0];assert not hit,(x,y,direction);rays+=1
dish,_=readglb('mining_dish.glb');dn={n['name']:n for n in dish['nodes']};assert {'dish_yaw','dish_pitch','focus',*[f'rim_{i}' for i in range(6)]}<=set(dn)
assert any(abs(v)>1 for v in dn['focus']['translation'])
pitch=dn['dish_pitch']['translation'];yaw=dn['dish_yaw']['translation'];focus=[dn['focus']['translation'][i]+pitch[i]+yaw[i] for i in range(3)]
assert focus[0]>50 and focus[1]>1400,focus
assembled,_=readglb('cargo_carrier_assembled.glb');total=sum(assembled['accessors'][p['indices']]['count']//3 for m in assembled['meshes'] for p in m['primitives']);assert total==report['triangles_with_dish'] and total<=40000
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'cargo_carrier.blend'))
em=bpy.data.objects['emissive'];letter_group=em.vertex_groups['label_texel_density'].index
letters=[v for v in em.data.vertices if any(g.group==letter_group for g in v.groups)]
assert letters and all(abs(v.co.x)<115 and abs(v.co.y)<8 and 100<v.co.z<160 for v in letters),'Hangar lettering moved during UV packing'
for name in report['meshes']:
    ob=bpy.data.objects[name];assert ob.location.length<1e-5;assert all(abs(s-1)<1e-5 for s in ob.scale)
    assert len(ob.data.uv_layers)==1
    for mat in ob.data.materials:
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE':assert node.image.packed_file
result={'status':'PASS','triangles':count,'triangles_with_dish':total,'texture_size':2048,'embedded_maps':4,'attachment_points':len(report['empties']),'uv_overlaps':0,'hangar_clearance_rays':rays,'length':max(xs)-min(xs),'dish_focus_world':focus,'packed_blend_textures':True,'cameras_lights_in_glb':False}
(ROOT/'validation.json').write_text(json.dumps(result,indent=2));print('VALIDATION_PASS',json.dumps(result),flush=True)
