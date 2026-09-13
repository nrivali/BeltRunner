import bpy, bmesh, math, json, struct, itertools
from mathutils import Vector
from pathlib import Path

OUT=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
bpy.context.preferences.filepaths.save_version=0
def C(p):return Vector((p[0],-p[2],p[1]))
def lin(v):return v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4
def rgb(h):return tuple(lin(int(h[i:i+2],16)/255) for i in (0,2,4))
source=bpy.data.images.load(str(OUT/'source/imagegen_panels.png'));source.pack()
PALETTE={'paint':'B4BCCF','trim':'3A4058','plate':'828CA9','amber':'F2A33A','rubber':'161D2A','glass':'B88942','cyan':'5ED3F0','red':'FF5A5A','green':'6BD69A','warm':'FFD9A0'}
MATS={};groups={};bevels={}
for name,h in PALETTE.items():
    m=bpy.data.materials.new('source_'+name);m.use_nodes=True;MATS[name]=m
    n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*rgb(h),1)
    bs.inputs['Metallic'].default_value=.3;bs.inputs['Roughness'].default_value=.46
    if name in ('paint','trim','plate','amber'):
        tc=n.new('ShaderNodeTexCoord');vm=n.new('ShaderNodeVectorMath');vm.operation='SCALE';vm.inputs[3].default_value=1.1
        l.new(tc.outputs['Generated'],vm.inputs[0]);tx=n.new('ShaderNodeTexImage');tx.image=source;tx.projection='BOX';tx.projection_blend=.06;l.new(vm.outputs[0],tx.inputs['Vector'])
        soften=n.new('ShaderNodeMixRGB');soften.blend_type='MIX';soften.inputs[0].default_value=.62;soften.inputs[1].default_value=(1,1,1,1);l.new(tx.outputs['Color'],soften.inputs[2])
        tint=n.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(*((1,1,1) if name=='paint' else rgb(h)),1);l.new(soften.outputs[0],tint.inputs[1]);l.new(tint.outputs[0],bs.inputs['Base Color'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.3;bump.inputs['Distance'].default_value=.015;l.new(tx.outputs['Color'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
    if name in ('cyan','red','green','warm'):
        bs.inputs['Emission Color'].default_value=(*rgb(h),1);bs.inputs['Emission Strength'].default_value=2.5

def mesh(group,vs,fs,mat='paint',bevel=.045):
    me=bpy.data.meshes.new(group);me.from_pydata([C(v) for v in vs],[],fs);me.update()
    ob=bpy.data.objects.new(group,me);scene.collection.objects.link(ob);me.materials.append(MATS[mat]);groups.setdefault(group,[]).append(ob);bevels[group]=bevel;return ob
def box(group,p,d,mat='paint',bevel=.045):
    a,b,c=[v/2 for v in d];x,y,z=p
    vs=[(x+i*a,y+j*b,z+k*c) for i,j,k in [(-1,-1,-1),(-1,-1,1),(-1,1,1),(-1,1,-1),(1,-1,-1),(1,-1,1),(1,1,1),(1,1,-1)]]
    return mesh(group,vs,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(0,3,7,4),(1,5,6,2)],mat,bevel)
def loft(group,sections,mat='paint',bevel=.045):
    # Octagonal cross sections along game Z: (z, half-width, bottom, top).
    vs=[]
    for z,w,b,t in sections:
        ch=min(.5,w*.23,(t-b)*.23)
        vs += [(-w+ch,b,z),(w-ch,b,z),(w,b+ch,z),(w,t-ch,z),(w-ch,t,z),(-w+ch,t,z),(-w,t-ch,z),(-w,b+ch,z)]
    fs=[tuple(range(7,-1,-1)),tuple(range(len(vs)-8,len(vs)))]
    for k in range(len(sections)-1):
        for j in range(8):fs.append((k*8+j,k*8+(j+1)%8,(k+1)*8+(j+1)%8,(k+1)*8+j))
    return mesh(group,vs,fs,mat,bevel)
def prism(group,outline,top,bottom,mat='paint',bevel=.045):
    vs=[(x,bottom,z) for x,z in outline]+[(x,top,z) for x,z in outline];n=len(outline)
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(group,vs,fs,mat,bevel)
def beam(group,a,b,r,mat='trim',n=6):
    aa=C(a);bb=C(b);delta=bb-aa
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=r,depth=delta.length,location=(aa+bb)*.5)
    ob=bpy.context.object;ob.rotation_euler=delta.to_track_quat('Z','Y').to_euler();ob.data.materials.append(MATS[mat]);groups.setdefault(group,[]).append(ob);bevels[group]=.025;return ob
def ring(group,p,ro,ri,depth,mat='trim',axis='z',n=16,ratio=1,bevel=.02):
    vs=[]
    for along,r in [(-depth/2,ro),(depth/2,ro*ratio),(-depth/2,ri),(depth/2,ri*ratio)]:
        for i in range(n):
            a=2*math.pi*i/n;u,v=math.cos(a)*r,math.sin(a)*r
            q=(u,v,along) if axis=='z' else (u,along,v)
            vs.append(tuple(p[j]+q[j] for j in range(3)))
    fs=[]
    for i in range(n):
        j=(i+1)%n;fs.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    return mesh(group,vs,fs,mat,bevel)
def empty(name,p):
    ob=bpy.data.objects.new(name,None);scene.collection.objects.link(ob);ob.location=C(p);ob.empty_display_size=.6;ob.empty_display_type='PLAIN_AXES';return ob

# Central pressure hull with compact blunt nose, stepped spine and armor shoulders.
loft('hull',[(-10.7,2.7,-1.55,1.65),(-7.5,3.25,-1.95,2.15),(-2.5,3.35,-1.95,2.25),(2.5,3.1,-1.7,1.8),(7.8,2.4,-1.2,.8),(11.8,1.8,-.85,.35),(13,1.1,-.55,.15)])
loft('hull_trim',[(-10.6,2.75,-1.75,-1.3),(-2.5,3.39,-2.12,-1.74),(5.5,2.6,-1.55,-1.2),(11.4,1.8,-.95,-.65)],'trim',.03)
loft('hull',[(-9.5,1.7,2.02,2.65),(-5.0,1.95,2.18,3.1),(-2.6,1.7,2.15,2.55)],'plate')
for s in (-1,1):
    for z in (-6,-2,2.5):
        box('hull_trim',(s*3.27,.3,z),(.18,1.75,2.2),'trim')
        box('hull',(s*3.38,.38,z),(.14,1.42,1.95),'plate')
    box('hull_trim',(s*3.25,-.5,-1),(1.0,.9,6.6),'trim')
    for k in range(4):box('hull_trim',(s*3.6,.25,-.3+k*.45),(.32,1.2,.14),'trim',.015)
    # Amber diagonal-like service bands are geometry, independent of tintable paint.
    box('hull_trim',(s*2.25,1.0,6.9),(.3,.1,1.2),'amber',.01)
    box('hull_trim',(s*.78,.14,12.75),(.55,.36,.16),'trim',.025)
    box('emissive',(s*.78,.14,12.86),(.38,.2,.025),'warm',.008)
# A raised, glazed single-seat cockpit; frame follows actual pane edges.
canopy=[(-2.08,1.45,6.6),(2.08,1.45,6.6),(2.55,2.35,-2.3),(-2.55,2.35,-2.3),(-1.47,2.1,5.5),(1.47,2.1,5.5),(1.9,4.2,-1.25),(-1.9,4.2,-1.25)]
mesh('canopy',canopy,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],'glass',0)
for i,j in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]:beam('cockpit_frame',canopy[i],canopy[j],.105,'trim',6)
box('cockpit',(0,2.37,-.25),(1.4,.32,1.3),'rubber')
box('cockpit',(0,3.05,-.85),(1.38,1.45,.32),'rubber')
box('cockpit',(0,3.7,-.9),(.8,.5,.38),'plate')
box('cockpit',(0,1.65,4.8),(2.3,.35,.75),'trim')
box('emissive',(0,1.85,4.65),(1.2,.025,.32),'cyan',.005)
for s in (-1,1):beam('cockpit',(s*.6,2.7,.8),(s*.6,2.9,1.15),.08,'rubber')
# Paired nacelle cores belong to the base ship. Three upgrade shells share the same interfaces.
for s in (-1,1):
    ob=loft('engine_core',[(-11.65,1.25,-1.25,1.25),(-10.3,1.42,-1.3,1.45),(-5,1.18,-1.05,1.45)],'trim',.025)
    for v in ob.data.vertices:v.co.x+=s*4.4
    ring('engine_core',(s*4.4,0,-12.25),1.25,1.08,1.2,'plate',ratio=.85)
    ring('emissive',(s*4.4,0,-12.75),1.07,.89,.06,'cyan')
    ring('emissive',(s*4.4,0,-11.92),.87,.02,.03,'cyan')
for level in (1,2,3):
    g=f'engine_nacelle_{level}'
    for s in (-1,1):
        ob=loft(g,[(-11.2,1.37,-1.4,1.65),(-9.3,1.43+.08*level,-1.4,1.75+.15*level),(-4.1+.28*level,1.18,-1.1,1.6)],'paint',.055)
        for v in ob.data.vertices:v.co.x+=s*4.4
        box(g,(s*4.4,1.8+.13*level,-8.2),(1.6,.18,1.25),'trim')
        for k in range(3):box(g,(s*4.4,1.91+.13*level,-8.7+k*.38),(1.35,.08,.12),'plate',.01)
        box(g,(s*(5.83+.045*level),.6,-7.8),(.1,.22,1.0+.4*level),'amber',.01)

# Four compact wing geometries. Common tip position keeps nav attachment names stable.
outlines={
 'delta':[(3,-4.4),(12,-5.6),(12,-4.2),(3,3.0)],
 'swept':[(3,-4.4),(12,-5.6),(12,-4.2),(5.1,-1.2),(3,3.0)],
 'forward':[(3,-4.4),(5.0,-4.6),(12,3.5),(11.7,5.3),(3,1.8)],
 'twin':[(3,-4.4),(12,-5.6),(12,-4.2),(3,-.7)]}
for name,outline in outlines.items():
    g='wings_'+name
    for s in (-1,1):
        pts=[(s*x,z) for x,z in outline];prism(g,pts,-.05,-.6,'paint',.055)
        if name=='twin':
            ob=loft(g,[(-9.6,.53,-.65,.3),(-3.0,.64,-.6,.55),(6.5,.45,-.4,.25)],'plate',.04)
            for v in ob.data.vertices:v.co.x+=s*9.2
        # Service stripe sits on flat wing top, distinct from repaintable hull.
        if name=='forward':stripe=[(s*9.7,2.2),(s*10.25,2.75),(s*11.5,4.7),(s*10.8,4.1)]
        else:stripe=[(s*9.6,-5.25),(s*10.25,-5.35),(s*10.25,-3.85 if name=='delta' else -4.1),(s*9.6,-3.35 if name=='delta' else -3.95)]
        prism(g,stripe,.015,-.045,'amber',.008)
        tipz=4.3 if name=='forward' else -4.85
        box(g,(s*11.91,-.05,tipz),(.16,.38,.9),'trim',.02)
        box(g,(s*12.01,-.04,tipz),(.055,.2,.58),'red' if s>0 else 'green',.005)

# Flank cargo upgrades: one mutually exclusive paired module per level.
for level in (1,2,3):
    g=f'cargo_pod_{level}';length=2.9+level*.9
    for s in (-1,1):
        ob=loft(g,[(2.8-length,.55+.12*level,-1.7,.45),(2.5,.65+.12*level,-1.8,.6),(3.1,.5,-1.5,.3)],'paint',.055)
        for v in ob.data.vertices:v.co.x+=s*4.3
        box(g,(s*(5.0+.1*level),-.35,1),(.08,.32,1.0),'amber',.01)
        for z in (2.0,3.3-length):box(g,(s*4.3,.61,z),(1.35+.15*level,.12,.22),'trim',.015)

# Chin turret. The upper rotating envelope remains below the hull throughout yaw.
MOUNT=(0,-4.5,7)
box('hull_trim',(0,-2.775,7),(.9,3.15,.85),'trim',.045)
ring('dish_base',MOUNT,.63,.2,.3,'plate',axis='y',n=16)
box('dish_yoke',(0,-4.7,7),(.66,.5,.75),'trim',.025)
for s in (-1,1):
    box('dish_yoke',(s*.91,-4.95,7.45),(.18,.65,1.55),'plate',.025)
    ring('dish_yoke',(s*.9,-4.9,7.9),.23,.06,.15,'amber',n=8)
# Parabolic dish faces game +Z. Back-to-front four radial rings.
vs=[];n=24
for r in (.04,.4,.85,1.22):
    for i in range(n):
        a=2*math.pi*i/n;vs.append((r*math.cos(a),-4.9+r*math.sin(a),8+.3*(r/1.22)**2))
fs=[]
for k in range(3):
    for i in range(n):fs.append((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i))
mesh('mining_dish',vs,fs,'plate',0)
ring('mining_dish',(0,-4.9,8.32),1.28,1.18,.12,'trim',n=24,bevel=0)
for i in range(6):
    a=math.pi*2*i/6;x=1.18*math.cos(a);y=-4.9+1.18*math.sin(a)
    ring('mining_dish',(x,y,8.43),.13,.025,.13,'amber',n=8,bevel=0)
for a in (math.pi/2,math.pi/2+2.094,math.pi/2+4.189):beam('mining_dish',(1.1*math.cos(a),-4.9+1.1*math.sin(a),8.36),(0,-4.9,9.25),.045,'trim',6)
for level in (1,2,3):
    g=f'laser_barrel_{level}';length=.38+level*.48
    ring(g,(0,-4.9,9.15+length*.5),.24+level*.035,.14,length,'plate',n=12)
    ring(g,(0,-4.9,9.15+length),.26+level*.035,.16,.1,'trim',n=12,bevel=0)
    ring(g,(0,-4.9,9.21+length),.15,.01,.03,'warm',n=12,bevel=0)

# Scanner arrays grow upward from the same flat deck attachment.
for level in (1,2,3):
    g=f'scanner_dish_{level}';rad=.45+level*.25;yy=3.7+.2*level
    box(g,(0,3.13,-5.9),(1.2,.2,1.1),'trim')
    box(g,(0,3.45,-5.9),(.28,.5,.28),'plate')
    # shallow horizontal dish opening upward
    vs=[];n=16
    for r,h in ((.02,0),(rad,.25)):
        for i in range(n):a=i*2*math.pi/n;vs.append((r*math.cos(a),yy+h,-5.9+r*math.sin(a)))
    mesh(g,vs,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],'plate',0)
    ring(g,(0,yy+.24,-5.9),rad+.05,rad-.03,.08,'trim',axis='y',n=16,bevel=0)
    beam(g,(0,yy,-5.9),(0,yy+.5,-5.9),.055,'amber',6)

# Consolidate each named component, correct normals, bevel and triangulate after UV baking.
objects={}
for group,obs in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();o=bpy.context.object;o.name=group
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bm=bmesh.new();bm.from_mesh(o.data)
    if group not in ('canopy','mining_dish') and not group.startswith('scanner_dish'):bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free()
    # Circular lips and tiny light/frame parts already have modeled edge profiles.
    # Avoid subdividing them again; spend the triangle budget on armor silhouettes.
    if bevels[group]>0 and group not in ('emissive','engine_core','cockpit_frame','mining_dish','dish_base','dish_yoke') and not group.startswith('scanner_dish'):
        mod=o.modifiers.new('Crisp bevels','BEVEL');mod.width=bevels[group];mod.segments=1;mod.affect='EDGES';mod.angle_limit=.6
        bpy.ops.object.modifier_apply(modifier=mod.name)
    while o.data.uv_layers:o.data.uv_layers.remove(o.data.uv_layers[0])
    o.data.uv_layers.new(name='UVMap');objects[group]=o

# All variants get their own non-overlapping UV islands in one shared atlas.
bpy.ops.object.select_all(action='DESELECT')
for o in objects.values():o.select_set(True)
bpy.context.view_layer.objects.active=objects['hull'];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.004,area_weight=.6,correct_aspect=True,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
print('GEOMETRY_READY',flush=True)

# Bake ImageGen paneling into the authored UV atlas. Only base color is baked;
# scene lighting remains physically computed at runtime / during Cycles renders.
maps={}
for key in ('basecolor','metallic_roughness','normal','emissive'):
    im=bpy.data.images.new('player_'+key,1024,1024,alpha=True)
    if key in ('normal','metallic_roughness'):im.colorspace_settings.name='Non-Color'
    maps[key]=im
scene.render.bake.margin=4;scene.render.bake.use_clear=True;scene.cycles.samples=1
records=[]
for name,m in MATS.items():
    nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');out=nt.nodes.get('Material Output')
    emit=nt.nodes.new('ShaderNodeEmission');src=bs.inputs['Base Color'];base_link=src.links[0].from_socket if src.is_linked else None
    records.append((name,nt,bs,out,emit,base_link,tuple(src.default_value)))
def bake_color(key):
    for name,nt,bs,out,emit,base_link,color in records:
        for lk in list(emit.inputs['Color'].links):nt.links.remove(lk)
        if key=='basecolor':
            if base_link:nt.links.new(base_link,emit.inputs['Color'])
            else:emit.inputs['Color'].default_value=color
        elif key=='metallic_roughness':emit.inputs['Color'].default_value=(1,.16 if name=='glass' else .5,.05 if name in ('glass','rubber') else .3,1)
        else:emit.inputs['Color'].default_value=(*rgb(PALETTE[name]),1) if name in ('cyan','red','green','warm') else (0,0,0,1)
        nt.links.new(emit.outputs[0],out.inputs['Surface'])
        node=nt.nodes.new('ShaderNodeTexImage');node.image=maps[key];nt.nodes.active=node
    bpy.ops.object.bake(type='EMIT')
    print('BAKED',key,flush=True)
for key in ('basecolor','metallic_roughness','emissive'):bake_color(key)
for name,nt,bs,out,emit,base_link,color in records:
    nt.links.new(bs.outputs[0],out.inputs['Surface']);node=nt.nodes.new('ShaderNodeTexImage');node.image=maps['normal'];nt.nodes.active=node
bpy.ops.object.bake(type='NORMAL')
for key,im in maps.items():
    im.filepath_raw=str(OUT/'textures'/f'player_{key}.png');im.file_format='PNG';im.save();im.pack()

# Runtime materials share the complete PBR texture set. Paint retains its own tint.
finalmats={}
for kind in ('paint','trim','glass','emissive'):
    m=bpy.data.materials.new(kind);m.use_nodes=True;nt=m.node_tree;bs=nt.nodes.get('Principled BSDF')
    def tex(key):n=nt.nodes.new('ShaderNodeTexImage');n.image=maps[key];return n.outputs['Color']
    base=tex('basecolor')
    if kind=='paint':
        mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*rgb('B4BCCF'),1);nt.links.new(base,mix.inputs[1]);base=mix.outputs[0]
    nt.links.new(base,bs.inputs['Base Color'])
    sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex('metallic_roughness'),sep.inputs['Color']);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    if kind!='glass':
        nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex('normal'),nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
    if kind=='emissive':nt.links.new(tex('emissive'),bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=3
    if kind=='glass':
        bs.inputs['Transmission Weight'].default_value=.65;bs.inputs['Alpha'].default_value=1;bs.inputs['IOR'].default_value=1.45
    finalmats[kind]=m
counts={}
for name,o in objects.items():
    kinds=[('paint' if m==MATS['paint'] else 'glass' if m==MATS['glass'] else 'emissive' if m in [MATS[k] for k in ('cyan','red','green','warm')] else 'trim') for m in o.data.materials]
    indices=[kinds[p.material_index] for p in o.data.polygons]
    o.data.materials.clear()
    for m in finalmats.values():o.data.materials.append(m)
    for p,k in zip(o.data.polygons,indices):p.material_index=list(finalmats).index(k)
    bpy.context.view_layer.objects.active=o;mod=o.modifiers.new('Triangulated','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    counts[name]=len(o.data.polygons)

# Exact game attachment names and local-space chin-dish rig.
anchors={name:empty(name,p) for name,p in {'dish_mount':MOUNT,'engine_l':(4.4,0,-12.85),'engine_r':(-4.4,0,-12.85),'nav_l':(12.04,-.04,-4.85),'nav_r':(-12.04,-.04,-4.85)}.items()}
yaw=empty('mining_dish_yaw',MOUNT);pitch=empty('mining_dish_pitch',(0,-4.9,7.9))
def parent_keep(o,parent):mat=o.matrix_world.copy();o.parent=parent;o.matrix_world=mat
bpy.context.view_layer.update();parent_keep(pitch,yaw)
for name in ('dish_yoke',):parent_keep(objects[name],yaw)
parent_keep(objects['mining_dish'],pitch)
parent_keep(objects['laser_barrel_1'],pitch)
for level in (1,2,3):
    objects[f'laser_barrel_{level}']['attachment_parent']='mining_dish_pitch'
# Barrel variants remain root nodes for interchangeability; consumers attach while preserving world transform.
focus=empty('focus',(0,-4.9,10.07));parent_keep(focus,pitch)
for i in range(6):a=i*math.pi/3;parent_keep(empty('rim_'+str(i),(1.18*math.cos(a),-4.9+1.18*math.sin(a),8.5)),pitch)
for name,o in objects.items():
    o['component']=name
    o['default_visible']=not (name.startswith('wings_') and name!='wings_delta' or any(name==f'{p}_{l}' for p in ('laser_barrel','cargo_pod','engine_nacelle','scanner_dish') for l in (2,3)))
    if name.startswith('wings_'):o['nav_l']=[12.04,-.04,4.3 if name=='wings_forward' else -4.85];o['nav_r']=[-12.04,-.04,4.3 if name=='wings_forward' else -4.85]
defaults=[name for name,o in objects.items() if o['default_visible']]
variants=[n for n in objects if n not in defaults]
assembled={}
for wing,level in itertools.product(outlines,(1,2,3)):
    active=[n for n in objects if not n.startswith(('wings_','laser_barrel_','cargo_pod_','engine_nacelle_','scanner_dish_'))]+['wings_'+wing]+[f'{p}_{level}' for p in ('laser_barrel','cargo_pod','engine_nacelle','scanner_dish')]
    assembled[f'{wing}_level_{level}']=sum(counts[n] for n in active)
radius=max(v.co.length for o in objects.values() for v in o.data.vertices if o.parent is None)
print('TRIANGLE_COUNTS',json.dumps(counts),flush=True)
assert max(assembled.values())<=8000,assembled
assert radius<=16, radius
report={'triangles_by_mesh':counts,'triangles_all_components':sum(counts.values()),'assembled_triangle_counts':assembled,'max_radius':radius,'forward':'+Z','up':'+Y','dimensions_approx':[24,10.5,26],'default_components':defaults,'optional_components':variants,'attachments':{n:[o.location.x,o.location.z,-o.location.y] for n,o in anchors.items()},'textures':'1024 x 1024; shared atlas baked in Blender from ImageGen source'}
(OUT/'asset_report.json').write_text(json.dumps(report,indent=2))
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:o.select_set(True)
scene['asset']='Belt Runner 3D / Player ship';scene['forward_in_glTF']='+Z';scene['default_wings']='wings_delta'
bpy.ops.export_scene.gltf(filepath=str(OUT/'player_ship.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_extras=True,export_cameras=False,export_lights=False)
# A default assembled scene plus a second component-library scene avoids stacked alternatives in viewers.
raw=(OUT/'player_ship.glb').read_bytes();ln,typ=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+ln]);tail=raw[20+ln:]
rootnodes=doc['scenes'][doc.get('scene',0)]['nodes'];opt=[i for i in rootnodes if doc['nodes'][i].get('name') in variants]
doc['scenes']=[{'name':'Player ship - delta - level 1','nodes':[i for i in rootnodes if i not in opt]},{'name':'Interchangeable components','nodes':opt}];doc['scene']=0
for material in doc['materials']:
    if material['name']=='paint':material['pbrMetallicRoughness']['baseColorFactor']=[*rgb('B4BCCF'),1]
payload=json.dumps(doc,separators=(',',':')).encode();payload+=b' '*((-len(payload))%4)
(OUT/'player_ship.glb').write_bytes(struct.pack('<III',0x46546c67,2,20+len(payload)+len(tail))+struct.pack('<II',len(payload),0x4e4f534a)+payload+tail)

# Presentation scene: broad realistic lights and transparent tinted canopy.
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.14,.18,.25,1);bg.inputs['Strength'].default_value=.4
def area(name,p,energy,size,col):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy*.55;data.shape='DISK';data.size=size;data.color=col
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=C(p);o.rotation_euler=(C((0,0,0))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key softbox',(12,24,14),16000,18,(.82,.9,1));area('Warm rim',(-18,14,-10),21000,14,(1,.76,.48));area('Front fill',(-10,8,18),7000,12,(.7,.83,1));area('Engine rim',(8,10,-22),12000,12,(.6,.8,1))
data=bpy.data.cameras.new('presentation_camera');cam=bpy.data.objects.new('presentation_camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO';data.clip_end=1000;data.clip_start=.1
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.cycles.samples=64
def configure(wing='delta',level=1):
    for name,o in objects.items():
        visible=(not name.startswith(('wings_','laser_barrel_','cargo_pod_','engine_nacelle_','scanner_dish_')) or name=='wings_'+wing or name in [f'{p}_{level}' for p in ('laser_barrel','cargo_pod','engine_nacelle','scanner_dish')])
        o.hide_render=not visible;o.hide_set(not visible)
def render(name,p,target=(0,0,0),scale=36):
    cam.location=C(p);cam.rotation_euler=(C(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale;scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
configure();render('preview_front',(28,18,32),(0,-.4,0),35);render('preview_rear',(-26,14,-32),(0,0,-1),35)
for wing in outlines:
    configure(wing);render('wings_'+wing,(0,42,0),(0,0,0),40)
configure('delta',3);render('preview_level_3',(28,18,32),(0,-.4,0),35)
configure();cam.location=C((28,18,32));cam.rotation_euler=(C((0,-.4,0))-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=35
scene.cycles.samples=96
for screen in bpy.data.screens:
    for area_ in screen.areas:
        if area_.type=='VIEW_3D':area_.spaces.active.clip_end=1000;area_.spaces.active.region_3d.view_distance=40;area_.spaces.active.region_3d.view_location=(0,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'player_ship.blend'))
print('PLAYER_SHIP_COMPLETE',json.dumps(report),flush=True)
