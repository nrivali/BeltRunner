import bpy, bmesh, math, random, json
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
def C(p):return Vector((p[0],-p[2],p[1]))
def lin(v):return v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4
def rgb(h):return tuple(lin(int(h[i:i+2],16)/255) for i in (0,2,4))
# Shards: base x/z, height, radius, horizontal lean x/z per height.
SPECS=[
 ('01_needle',20,'F2A33A',(7,5,2.1),[(0,0,18,2.2,.1,.025),(-3.7,.4,8.4,1.4,-.4,.07),(3.1,1.0,9.8,1.45,.4,.03)]),
 ('02_fan',30,'35D6C2',(15,7,2.8),[(-8,1,14,2,-.55,.04),(-4,-1,21,2.5,-.25,-.06),(0,-.6,28,2.8,.02,0),(4,0,20,2.45,.35,.05),(8,1,13.5,1.9,.65,.06)]),
 ('03_crown',40,'8CDCF0',(13,10,3.8),[(0,-1,38,4.2,.035,0),(-6,0,21,2.65,-.22,.1),(6,1,19,2.5,.25,.09),(-3.5,5,13.5,2,-.35,.18)]),
 ('04_split_spire',60,'AE80ED',(15,9,4.5),[(-4,-1,58,5,.075,0),(6,0,39,3.9,.13,.05),(10,4,16,2.2,.38,.08)]),
 ('05_ridge',25,'467BE8',(22,9,3.2),[(-14,-1,23,3.6,.75,.04),(-1,0,16.5,3.25,1.05,.04),(12,1,11.5,2.65,1.25,.04)]),
 ('06_bloom',45,'55C987',(16,11,4.0),[(0,-1,43,4.4,.02,0),(-6,-1,29,3.4,-.32,-.06),(6,-2,31,3.2,.3,-.02),(-7,5,20,2.7,-.45,.15),(8,4,17,2.3,.4,.14)])]

def reset():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene.render.engine='CYCLES';scene.cycles.use_denoising=True;scene.cycles.samples=64
    bpy.context.preferences.filepaths.save_version=0
    return scene
def sources():
    return {k:bpy.data.images.load(str(ROOT/'source'/f'imagegen_{k}.png'),check_existing=True) for k in ('crystal','asteroid')}
def source_materials(images):
    mats=[]
    for kind in ('crystal_body','crystal_emissive','asteroid_matrix'):
        rock=kind=='asteroid_matrix';m=bpy.data.materials.new('source_'+kind);m.use_nodes=True
        nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');out=nt.nodes.get('Material Output')
        tc=nt.nodes.new('ShaderNodeTexCoord');tex=nt.nodes.new('ShaderNodeTexImage');tex.image=images['asteroid' if rock else 'crystal'];tex.projection='BOX';tex.projection_blend=.08
        nt.links.new(tc.outputs['Generated'],tex.inputs['Vector'])
        soften=nt.nodes.new('ShaderNodeMixRGB');soften.blend_type='MIX';soften.inputs[0].default_value=.82 if rock else .72;soften.inputs[1].default_value=(.08,.08,.08,1) if rock else (.65,.65,.65,1);nt.links.new(tex.outputs['Color'],soften.inputs[2]);nt.links.new(soften.outputs[0],bs.inputs['Base Color'])
        bs.inputs['Metallic'].default_value=.2;bs.inputs['Roughness'].default_value=.86 if rock else .24
        bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.6 if rock else .22;bump.inputs['Distance'].default_value=.2 if rock else .045
        nt.links.new(tex.outputs['Color'],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
        mats.append(m)
    return mats

def geometry(key,height,foot,shards,mats,seed):
    rng=random.Random(seed);verts=[];faces=[];mi=[]
    def append(vs,fs,mat):
        off=len(verts);verts.extend(vs);faces.extend(tuple(off+i for i in f) for f in fs)
        mi.extend(mat if isinstance(mat,list) else [mat]*len(fs))
    rx,rz,hh=foot;n=14
    lower=[];mid=[]
    for i in range(n):
        a=i*2*math.pi/n;f=rng.uniform(.89,1.08);lower.append((rx*math.cos(a)*f,0,rz*math.sin(a)*f));mid.append((rx*.82*math.cos(a)*f,hh*rng.uniform(.55,.95),rz*.82*math.sin(a)*f))
    vs=lower+mid+[(0,hh*1.25,0)]
    fs=[tuple(range(n-1,-1,-1))]
    for i in range(n):j=(i+1)%n;fs.extend([(i,j,n+j,n+i),(n+i,n+j,2*n)])
    append(vs,fs,2)
    # Small chunks intersect the parent rocky foot rather than floating beside it.
    for i in range(9):
        a=i*2*math.pi/9+rng.uniform(-.16,.16);p=C((math.cos(a)*rx*.72,hh*.5,math.sin(a)*rz*.72))
        bm=bmesh.new();bmesh.ops.create_icosphere(bm,subdivisions=1,radius=1);bm.verts.ensure_lookup_table()
        sz=(rx*rng.uniform(.16,.24),rz*rng.uniform(.23,.35),hh*rng.uniform(.6,1.05))
        # Blender axes: x horizontal, y depth, z height. Flatten underside to mounting plane.
        vs=[]
        for v in bm.verts:
            co=Vector((v.co.x*sz[0],v.co.y*sz[1],v.co.z*sz[2]))+p;co.z=max(0,co.z)
            vs.append((co.x,co.z,-co.y))
        fs=[tuple(v.index for v in f.verts) for f in bm.faces];append(vs,fs,2);bm.free()
    for si,(x,z,h,r,leanx,leanz) in enumerate(shards):
        # Twelve-point cross section: six broad facets separated by narrow beveled edges.
        angle=rng.uniform(0,.45);corners=[Vector((math.cos(angle+i*math.pi/3),math.sin(angle+i*math.pi/3))) for i in range(6)]
        section=[]
        for i,q in enumerate(corners):section.extend([q.lerp(corners[(i-1)%6],.085),q.lerp(corners[(i+1)%6],.085)])
        vs=[];rooty=hh*.22
        for t,scale in ((0,.68),(.19,1),(.76,.88)):
            for q in section:vs.append((x+q.x*r*scale+leanx*h*t,rooty+h*t,z+q.y*r*scale+leanz*h*t))
        vs.append((x+leanx*h+r*.12,rooty+h,z+leanz*h-r*.12))
        fs=[tuple(range(11,-1,-1))];idx=[0]
        for k in range(2):
            for j in range(12):
                fs.append((k*12+j,k*12+(j+1)%12,(k+1)*12+(j+1)%12,(k+1)*12+j))
                # Narrow edge slivers, not full luminous sides.
                idx.append(1 if k==1 and j in (0,6) else 0)
        for j in range(12):fs.append((24+j,24+(j+1)%12,36));idx.append(1 if j in (0,1) else 0)
        append(vs,fs,idx)
    factor=height/max(v[1] for v in verts)
    verts=[C(tuple(c*factor for c in v)) for v in verts]
    me=bpy.data.meshes.new('ore_cluster_'+key);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new('ore_cluster_'+key,me);bpy.context.scene.collection.objects.link(ob)
    for m in mats:me.materials.append(m)
    for p,i in zip(me.polygons,mi):p.material_index=i
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    ob.data.uv_layers.new(name='UVMap');bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.012,area_weight=.4,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
    return ob

def bake(ob,mats,out):
    scene=bpy.context.scene;scene.cycles.samples=1;scene.render.bake.margin=3
    maps={}
    for key in ('basecolor','metallic_roughness','normal','emissive'):
        im=bpy.data.images.new(ob.name+'_'+key,width=512,height=512,alpha=True)
        if key in ('normal','metallic_roughness'):im.colorspace_settings.name='Non-Color'
        maps[key]=im
    records=[]
    for i,m in enumerate(mats):
        nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');outnode=nt.nodes.get('Material Output');base=bs.inputs['Base Color'].links[0].from_socket;emit=nt.nodes.new('ShaderNodeEmission')
        records.append((i,nt,bs,outnode,base,emit))
    for key in ('basecolor','metallic_roughness','emissive','normal'):
        for i,nt,bs,outnode,base,emit in records:
            for link in list(emit.inputs[0].links):nt.links.remove(link)
            if key=='normal':nt.links.new(bs.outputs[0],outnode.inputs['Surface'])
            else:
                if key=='basecolor':nt.links.new(base,emit.inputs[0])
                elif key=='metallic_roughness':emit.inputs[0].default_value=(1,.86 if i==2 else .24,.2,1)
                elif i==1:nt.links.new(base,emit.inputs[0])
                else:emit.inputs[0].default_value=(0,0,0,1)
                nt.links.new(emit.outputs[0],outnode.inputs['Surface'])
            node=nt.nodes.new('ShaderNodeTexImage');node.image=maps[key];nt.nodes.active=node
        bpy.ops.object.bake(type='NORMAL' if key=='normal' else 'EMIT')
        im=maps[key];im.filepath_raw=str(out/'textures'/f'{key}.png');im.file_format='PNG';im.save();im.pack()
    return maps

def final_materials(ob,maps,color):
    saved=[p.material_index for p in ob.data.polygons];ob.data.materials.clear()
    for kind in ('crystal_body','crystal_emissive','asteroid_matrix'):
        m=bpy.data.materials.new(kind);m.use_nodes=True;nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');ore=kind!='asteroid_matrix'
        def tex(key):node=nt.nodes.new('ShaderNodeTexImage');node.image=maps[key];return node.outputs[0]
        base=tex('basecolor')
        if ore:
            mult=nt.nodes.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1;mult.inputs[2].default_value=(*rgb(color),1);nt.links.new(base,mult.inputs[1]);base=mult.outputs[0]
        nt.links.new(base,bs.inputs['Base Color'])
        sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex('metallic_roughness'),sep.inputs[0]);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
        nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex('normal'),nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
        if ore:bs.inputs['Transmission Weight'].default_value=.18;bs.inputs['IOR'].default_value=1.48
        if kind=='crystal_emissive':
            mult=nt.nodes.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1;mult.inputs[2].default_value=(*rgb(color),1);nt.links.new(tex('emissive'),mult.inputs[1]);nt.links.new(mult.outputs[0],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=1.8
        ob.data.materials.append(m)
    for p,i in zip(ob.data.polygons,saved):p.material_index=i

def studio(scene,height):
    scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.1,.13,.18,1);bg.inputs[1].default_value=.5
    def light(name,pos,power,size,col):
        data=bpy.data.lights.new(name,'AREA');data.energy=height*height*power;data.shape='DISK';data.size=height*size;data.color=col
        o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=C(tuple(v*height for v in pos));o.rotation_euler=(C((0,height*.35,0))-o.location).to_track_quat('-Z','Y').to_euler()
    light('Large neutral softbox',(-1.6,2.3,1.8),42,1.7,(1,.93,.82));light('Cool rim',(1.3,1.8,-1.4),65,1.2,(.7,.84,1));light('Front fill',(1.8,.8,2.3),14,1.8,(.86,.93,1))
    bpy.ops.mesh.primitive_plane_add(size=height*100,location=(0,0,-.035));floor=bpy.context.object;floor.name='presentation_floor'
    mat=bpy.data.materials.new('Studio charcoal');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.022,.028,.039,1);bs.inputs['Roughness'].default_value=.74;floor.data.materials.append(mat)
    data=bpy.data.cameras.new('preview_camera');cam=bpy.data.objects.new('preview_camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO';data.clip_start=.01;data.clip_end=height*200
    scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.cycles.samples=96
    return cam
def render(scene,cam,ob,out,back=False):
    pts=[v.co for v in ob.data.vertices];height=max(v.z for v in pts);width=max(max(v.x for v in pts)-min(v.x for v in pts),max(v.y for v in pts)-min(v.y for v in pts))
    target=C((0,height*.46,0));direction=C((-1.25,.6,-2.2) if back else (1.25,.6,2.2)).normalized()
    cam.location=target+direction*height*4;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=max(height*1.45,width*1.32)
    scene.render.filepath=str(out/('preview_rear.png' if back else 'preview_front.png'));bpy.ops.render.render(write_still=True)

reports=[];assets=[]
for si,(key,height,color,foot,shards) in enumerate(SPECS):
    scene=reset();out=ROOT/key;(out/'textures').mkdir(parents=True,exist_ok=True)
    images=sources();mats=source_materials(images);ob=geometry(key,height,foot,shards,mats,101+si)
    maps=bake(ob,mats,out);final_materials(ob,maps,color)
    bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('Triangulated','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    triangles=len(ob.data.polygons);assert triangles<=800,triangles
    ob['asset_id']=key;ob['surface_axis']='+Y';ob['ore_tint']='#'+color;ob['height_units']=height;ob['triangles']=triangles
    bpy.ops.export_scene.gltf(filepath=str(out/(ob.name+'.glb')),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_extras=True,export_cameras=False,export_lights=False)
    # Preserve the actual PBR tint factors where Blender's graph exporter omits MixRGB constants.
    import struct
    p=out/(ob.name+'.glb');raw=p.read_bytes();n,_=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+n]);tail=raw[20+n:]
    for material in doc['materials']:
        material['name']=material['name'].split('.')[0]
        if material['name'].startswith('crystal_'):
            material['pbrMetallicRoughness']['baseColorFactor']=[*rgb(color),1]
        if material['name'].startswith('crystal_emissive'):material['emissiveFactor']=list(rgb(color));material.setdefault('extensions',{})['KHR_materials_emissive_strength']={'emissiveStrength':1.8}
    payload=json.dumps(doc,separators=(',',':')).encode();payload+=b' '*((-len(payload))%4);p.write_bytes(struct.pack('<III',0x46546c67,2,20+len(payload)+len(tail))+struct.pack('<II',len(payload),0x4e4f534a)+payload+tail)
    dims=[max(v.co[i] for v in ob.data.vertices)-min(v.co[i] for v in ob.data.vertices) for i in (0,2,1)]
    report={'asset':ob.name,'mesh':ob.name,'empties':[],'triangles':triangles,'shards':len(shards),'dimensions_xyz':dims,'height':height,'origin':'mounting footprint centre at ground plane','up':'+Y','forward':'+Z','materials':['crystal_body','crystal_emissive','asteroid_matrix'],'textures':512,'color':'#'+color}
    (out/'asset_report.json').write_text(json.dumps(report,indent=2));reports.append(report)
    cam=studio(scene,height);render(scene,cam,ob,out);render(scene,cam,ob,out,True)
    # Leave the Blender camera on the front view, and pack the original sources as well.
    target=C((0,height*.46,0));cam.location=target+C((1.25,.6,2.2)).normalized()*height*4;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    for image in images.values():image.pack()
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(ob.name+'.blend')))
    # Preserve model datablocks for the final presentation scene across reset().
    clone=ob.copy();clone.data=ob.data.copy();clone.name=ob.name;assets.append(clone)
    print('ASSET_DONE',key,triangles,flush=True)

scene=reset();cam=studio(scene,90);scene.render.resolution_x=1800;scene.render.resolution_y=1400;scene.cycles.samples=96
for i,ob in enumerate(assets):
    scene.collection.objects.link(ob);ob.location=C(((i%3-1)*70,0,-65 if i<3 else 65))
    # Presentation labels are not included in any asset GLB.
    bpy.ops.object.text_add(location=ob.location+C((0,.12,23)))
    text=bpy.context.object;text.data.body=SPECS[i][0].replace('_',' / ',1).replace('_',' ').upper();text.data.align_x='CENTER';text.data.size=3.2
    text.rotation_euler=(0,0,0)
    mat=bpy.data.materials.get('Presentation label')
    if not mat:
        mat=bpy.data.materials.new('Presentation label');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.6,.65,.74,1);bs.inputs['Emission Color'].default_value=(.2,.24,.3,1);bs.inputs['Emission Strength'].default_value=.3
    text.data.materials.append(mat)
target=C((0,14,0));cam.location=C((0,220,300));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=260
scene.render.filepath=str(ROOT/'preview_collection.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'ore_clusters_studio.blend'))
(ROOT/'asset_manifest.json').write_text(json.dumps(reports,indent=2));print('ALL_CLUSTERS_COMPLETE',flush=True)
