import bpy, bmesh, math, random, json, os
import numpy as np
from mathutils import Vector
from pathlib import Path

OUT=Path(__file__).resolve().parent
random.seed(18)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
# Model in game coordinates; export's Z-up to Y-up conversion recovers (x,y,z).
def coord(p): return (p[0],-p[2],p[1])
colors={'light':'B4BCCF','mid':'9AA4BF','plate':'828CA9','dark':'3A4058','structure':'56608A','cyan':'5ED3F0','amber':'F2A33A','window':'FFD9A0','red':'FF5A5A','green':'6BD69A'}
def linear(c): return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
palette={}
for name,h in colors.items():
    rgb=tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
    m=bpy.data.materials.new(name); m.diffuse_color=(*rgb,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*map(linear,rgb),1)
    bs.inputs['Metallic'].default_value=.3; bs.inputs['Roughness'].default_value=.48
    if name in ('cyan','window','red','green'):
        bs.inputs['Emission Color'].default_value=(*map(linear,rgb),1); bs.inputs['Emission Strength'].default_value=3
    palette[name]=m
groups={k:[] for k in ('hull','interior','emissive','glass')}
def mesh(name,verts,faces,mat='mid',group='hull'):
    me=bpy.data.meshes.new(name); me.from_pydata([coord(v) for v in verts],[],faces); me.update()
    ob=bpy.data.objects.new(name,me); scene.collection.objects.link(ob); me.materials.append(palette[mat]); groups[group].append(ob); return ob
def box(name,c,d,mat='mid',group='hull'):
    x,y,z=c; a,b,c=[v/2 for v in d]
    vs=[(x+i*a,y+j*b,z+k*c) for i,j,k in [(-1,-1,-1),(-1,-1,1),(-1,1,1),(-1,1,-1),(1,-1,-1),(1,-1,1),(1,1,1),(1,1,-1)]]
    return mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)],mat,group)
def ring(name,center,ro,ri,depth,axis='x',mat='structure',group='hull',n=24,backscale=1):
    vs=[]
    for along,r in [(-depth/2,ro),(depth/2,ro*backscale),(-depth/2,ri),(depth/2,ri*backscale)]:
        for i in range(n):
            a=i*2*math.pi/n; u,v=math.cos(a)*r, math.sin(a)*r
            q=(along,u,v) if axis=='x' else (u,along,v)
            vs.append(tuple(center[j]+q[j] for j in range(3)))
    fs=[]
    for i in range(n):
        j=(i+1)%n
        fs.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    return mesh(name,vs,fs,mat,group)
def empty(name,p):
    ob=bpy.data.objects.new(name,None); scene.collection.objects.link(ob); ob.location=coord(p); ob.empty_display_type='PLAIN_AXES'; ob.empty_display_size=80; return ob

# Main hull, four solids leave an unobstructed 840 x 352 transverse passage.
box('aft_pressure_hull',(-1840,0,0),(2840,1080,1800),'dark')
box('forward_pressure_hull',(2060,0,0),(3280,1080,1800),'dark')
box('hangar_upper_hull',(0,358,0),(840,364,1800),'dark')
box('hangar_lower_hull',(0,-358,0),(840,364,1800),'dark')
# Wedge prow continues to exact x=4600.
mesh('prow',[(3700,-540,-900),(3700,-540,900),(3700,540,900),(3700,540,-900),(4600,-90,0),(4600,90,0)],[(0,4,5,3),(1,2,5,4),(3,5,2),(0,1,4),(0,3,2,1)],'light')
# Side plates, panel seams, rails and utility strips.
for s in (-1,1):
    for i,x in enumerate(range(-2960,3501,470)):
        for y in (-343,343):
            box('side_plate',(x,y,s*910),(448,352,20),'light' if i%3 else 'mid')
        if abs(x)>640:
            box('side_mid_plate',(x,0,s*911),(448,280,22),'mid')
            box('panel_inset',(x-80,15,s*927),(175,115,10),'plate')
        for y in (-472,472):
            box('window_recess',(x,y,s*926),(375,61,14),'dark')
            for q in range(5): box('window',(x-148+q*74,y,s*935),(57,29,6),'window','glass')
        for y in (-410,410):
            for dx in (-198,198):box('panel_fastener',(x+dx,y,s*926),(10,10,7),'structure')
    for x in (-3180,-2260,-1320,-490,490,1560,2500,3590):
        box('vertical_rib',(x,0,s*950),(63,1060,75),'structure')
        box('rib_cap',(x,0,s*995),(25,770,15),'plate')
        for y in (-390,390):box('rib_clamp',(x,y,s*995),(86,65,30),'light')
    for y in (-533,533):box('edge_rail',(150,y,s*925),(7040,26,48),'structure')
    # Exactly dimensioned mouth interior; rim stays outside the opening.
    for y in (-203,203):box('hangar_rim',(0,y,s*944),(952,54,88),'light')
    for x in (-447,447):box('hangar_rim',(x,0,s*944),(54,352,88),'light')
    for x in (-450,450):
        for y in (-205,205):
            box('field_emitter_post',(x,y,s*1000),(86,90,40),'dark')
            box('field_emitter',(x,y,s*1023),(32,50,8),'cyan','emissive')
# Roof and belly tiled plating, recesses, amber service markings.
for x in range(-2930,3500,520):
    for z in (-650,-215,215,650):
        for y in (-550,550):box('deck_plate',(x,y,z),(498,20,409),'mid' if z<0 else 'light')
    for z in (-795,795):
        box('deck_conduit',(x,577,z),(470,25,24),'structure')
    if x<0:
        box('roof_vent_base',(x,568,0),(260,20,230),'dark')
        for k in range(7):box('roof_vent_fin',(x-105+k*35,589,0),(14,24,208),'structure')
for z in (-830,830):box('prow_service_stripe',(3470,566,z),(260,9,26),'amber')
# Interior floor at -150 keeps specified pad centers visible.
box('hangar_floor',(0,-163,0),(840,26,1800),'plate','interior')
box('hangar_ceiling',(0,185,0),(840,18,1800),'structure','interior')
for z in range(-750,751,250):
    for x in (-413,413):
        box('interior_wall_panel',(x,8,z),(14,290,228),'plate','interior')
        box('interior_column',(x-12*(1 if x>0 else -1),0,z-115),(22,332,22),'structure','interior')
    for x in (-250,250):
        box('ceiling_fixture',(x,167,z),(150,18,70),'dark','interior')
        box('ceiling_light',(x,155,z),(115,5,42),'window','emissive')
for z in (-525,525):
    box('landing_pad',(0,-145,z),(300,14,300),'dark','interior')
    for x in (-145,145):box('pad_light',(x,-136,z),(5,4,290),'cyan','emissive')
    for dz in (-145,145):box('pad_light',(0,-136,z+dz),(290,4,5),'cyan','emissive')
    box('pad_center_mark',(0,-135,z),(65,3,10),'amber','interior')
box('cargo_drop_pad',(250,-137,0),(230,14,240),'structure','interior')
for z in (-110,110):box('drop_edge',(250,-128,z),(215,4,8),'amber','interior')
box('sign_backing',(388,90,0),(20,95,320),'dark','interior')
bpy.ops.object.text_add(location=coord((374,90,0)))
ob=bpy.context.object; ob.name='cargo_drop_sign'; ob.data.body='CARGO DROP'; ob.data.align_x='CENTER'; ob.data.align_y='CENTER'; ob.data.size=38; ob.data.extrude=.4
# Text plane normal faces down the x axis, local horizontal follows game z.
ob.rotation_euler=(math.pi/2,0,-math.pi/2); ob.data.materials.append(palette['amber'])
bpy.ops.object.convert(target='MESH'); groups['interior'].append(ob)
# Bridge pedestal and armored wheelhouse.
box('bridge_pedestal',(900,590,0),(1050,80,930),'structure')
box('bridge_block',(900,700,0),(840,200,730),'light')
box('bridge_window_band',(912,731,0),(856,67,745),'dark')
for s in (-1,1):
    for x in (600,800,1000,1200):box('bridge_window',(x,734,s*378),(172,40,7),'window','glass')
for z in (-260,-130,0,130,260):box('bridge_front_window',(1344,734,z),(7,40,108),'window','glass')
box('bridge_roof',(900,817,0),(900,35,805),'mid')
for z in (-270,270):box('bridge_roof_equipment',(830,854,z),(270,42,140),'plate')
# Mast only: dish is asset 4, mount retained for the separate animated model.
box('mast_base',(-40,588,0),(360,76,310),'structure')
box('mast',(-40,795,0),(105,340,105),'plate')
box('mast_cap',(-40,980,0),(180,30,180),'light')
empty('dish_mount',(-40,995,0))
for z in (-110,110):
    box('mast_brace',(-40,737,z),(55,230,35),'dark')
    box('antenna',(-170,855,z),(15,480,15),'structure')
    box('antenna_beacon',(-170,1100,z),(22,20,22),'red','emissive')
# Three hollow engine bells, rear lip at x=-3550, centers exactly as specified.
box('stern_engine_block',(-3240,0,0),(160,1010,1770),'structure')
for i,z in enumerate((-540,0,540)):
    ring('engine_bell',(-3425,0,z),240,205,250,backscale=.76,mat='structure')
    ring('engine_lip',(-3538,0,z),240,214,24,mat='light')
    ring('engine_inner_glow',(-3505,0,z),213,197,12,mat='cyan',group='emissive')
    ring('engine_throat',(-3318,0,z),159,1,8,mat='cyan',group='emissive')
    for k in range(8):
        a=2*math.pi*k/8
        box('engine_mount',(-3268,math.cos(a)*206,z+math.sin(a)*206),(70,28,28),'plate')
    empty('engine_'+str(i),(-3480,0,z))
# Dock rail supports reach the specified off-flank drone docking positions.
for i,x in enumerate((760,850,940)):
    box('drone_dock_arm',(x,-95,1215),(42,65,630),'structure')
    box('drone_dock_head',(x,-80,1500),(70,40,85),'plate')
    box('dock_status',(x,-56,1500),(30,6,24),'green','emissive')
    empty('drone_dock_'+str(i),(x,-60,1500))
for n,p in {'hangar_mouth_pos':(0,0,900),'hangar_mouth_neg':(0,0,-900),'pad_pos':(0,-138,525),'pad_neg':(0,-138,-525),'drop_pad':(250,-130,0),'bridge_windows':(900,734,0)}.items():empty(n,p)

# Consolidate draw calls while retaining the four requested material groups.
final=[]
for group,objects in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]; bpy.ops.object.join(); o=bpy.context.object; o.name=group
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bm=bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(o.data); bm.free()
    if group in ('hull','interior'):
        mod=o.modifiers.new('manufactured_edge_bevel','BEVEL'); mod.width=5 if group=='hull' else 1.5; mod.segments=1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    final.append(o)

# One shared 2048 PBR atlas, one nonoverlapping UV set across every surface.
polys=[(o,p) for o in final for p in o.data.polygons]
grid=math.ceil(math.sqrt(len(polys))); tile=2048//grid
assert tile>=6, 'Atlas too dense'
base=np.ones((2048,2048,4),dtype=np.float32); base[:,:,:3]=.15
emit=np.zeros_like(base); emit[:,:,3]=1
mr=np.ones_like(base); mr[:,:,1]=.49; mr[:,:,2]=.3
normal=np.ones_like(base); normal[:,:,:3]=(.5,.5,1)
for o in final:
    while o.data.uv_layers:o.data.uv_layers.remove(o.data.uv_layers[0])
    o.data.uv_layers.new(name='UVMap')
for index,(o,p) in enumerate(polys):
    tx=(index%grid)*tile; ty=(index//grid)*tile
    color=o.data.materials[p.material_index].diffuse_color[:3]
    base[ty:ty+tile,tx:tx+tile,:3]=tuple(map(linear,color))
    if o.name in ('emissive','glass'):emit[ty:ty+tile,tx:tx+tile,:3]=tuple(map(linear,color))
    # Project each planar polygon inside its own padded tile.
    points=[o.data.vertices[v].co for v in p.vertices]; drop=max(range(3),key=lambda i:abs(p.normal[i])); axes=[i for i in range(3) if i!=drop]
    lo=[min(v[a] for v in points) for a in axes]; hi=[max(v[a] for v in points) for a in axes]
    for li,v in zip(p.loop_indices,points):
        uv=[(v[a]-lo[k])/max(hi[k]-lo[k],1e-6) for k,a in enumerate(axes)]
        o.data.uv_layers.active.data[li].uv=((tx+1.5+uv[0]*(tile-3))/2048,(ty+1.5+uv[1]*(tile-3))/2048)
def saveimg(name,array,noncolor=False):
    im=bpy.data.images.new(name,width=2048,height=2048,alpha=True)
    if noncolor:im.colorspace_settings.name='Non-Color'
    im.pixels.foreach_set(array.ravel()); im.filepath_raw=str(OUT/'textures'/f'{name}.png'); im.file_format='PNG'; im.save(); return im
maps={'base':saveimg('cargo_basecolor',base),'mr':saveimg('cargo_metallic_roughness',mr,True),'normal':saveimg('cargo_normal',normal,True),'emission':saveimg('cargo_emissive',emit)}
for o in final:
    mat=bpy.data.materials.new('cargo_'+o.name); mat.use_nodes=True; nt=mat.node_tree; bs=nt.nodes.get('Principled BSDF')
    def tex(key):
        t=nt.nodes.new('ShaderNodeTexImage'); t.image=maps[key]; t.interpolation='Linear'; return t.outputs['Color']
    nt.links.new(tex('base'),bs.inputs['Base Color'])
    split=nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(tex('mr'),split.inputs['Color']); nt.links.new(split.outputs['Green'],bs.inputs['Roughness']); nt.links.new(split.outputs['Blue'],bs.inputs['Metallic'])
    nm=nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tex('normal'),nm.inputs['Color']); nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
    if o.name in ('emissive','glass'):
        nt.links.new(tex('emission'),bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value=3 if o.name=='emissive' else 1.8
    if o.name=='glass':bs.inputs['Roughness'].default_value=.22
    o.data.materials.clear(); o.data.materials.append(mat)
    for p in o.data.polygons:p.material_index=0
    bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('triangulated_export','TRIANGULATE'); bpy.ops.object.modifier_apply(modifier=mod.name)
    # Flat faces with split bevel geometry produce readable manufactured edges.
triangles=sum(len(o.data.polygons) for o in final)
assert triangles<=40000, triangles
for im in maps.values():im.pack()
bpy.ops.object.select_all(action='DESELECT')
for o in list(final)+[o for o in scene.objects if o.type=='EMPTY']:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'cargo_carrier.glb'),export_format='GLB',use_selection=True,export_yup=True,export_cameras=False,export_lights=False,export_apply=True)
report={'triangles':triangles,'meshes':[o.name for o in final],'empties':{o.name:list((o.location.x,o.location.z,-o.location.y)) for o in scene.objects if o.type=='EMPTY'},'atlas_size':2048,'forward':'+X','up':'+Y','dish':'Separate asset 4; carrier includes mast and dish_mount.'}
(OUT/'asset_report.json').write_text(json.dumps(report,indent=2))

# Physically based studio setup kept in .blend, excluded from exported glTF.
scene.render.engine='CYCLES'; scene.cycles.samples=48; scene.cycles.use_denoising=True
scene.world.color=(.13,.13,.13); scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background'); bg.inputs['Color'].default_value=(.16,.2,.29,1); bg.inputs['Strength'].default_value=.38
def area(name,pos,power,size,color,target=(300,0,0)):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power*.45; data.shape='DISK'; data.size=size; data.color=color
    ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob); ob.location=coord(pos); ob.rotation_euler=(Vector(coord(target))-ob.location).to_track_quat('-Z','Y').to_euler()
area('large_softbox',(1200,6500,4000),2.8e9,6500,(.84,.9,1))
area('warm_rim',(-2600,3800,-4400),3.4e9,4800,(1,.76,.53))
area('front_fill',(6600,1800,5000),1.1e9,4500,(.65,.8,1))
area('stern_fill',(-6500,1800,2500),1.4e9,3500,(.65,.79,1))
for z in (-650,0,650):area('hangar_bounce',(0,145,z),26000,220,(1,.85,.65),target=(0,-150,z))
camdata=bpy.data.cameras.new('preview_camera'); cam=bpy.data.objects.new('preview_camera',camdata); scene.collection.objects.link(cam); scene.camera=cam
camdata.type='ORTHO'; camdata.clip_end=100000; camdata.clip_start=1
scene.render.resolution_x=1800; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
def render(name,pos,target,scale):
    cam.location=coord(pos); cam.rotation_euler=(Vector(coord(target))-cam.location).to_track_quat('-Z','Y').to_euler(); camdata.ortho_scale=scale
    scene.render.filepath=str(OUT/f'{name}.png'); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cargo_carrier.blend')); bpy.ops.render.render(write_still=True)
render('preview_front',(9400,4900,14600),(350,150,0),10500)
render('preview_rear',(-10200,5400,11700),(200,100,0),10300)
camdata.type='PERSP'; camdata.lens=22
render('preview_hangar',(0,45,1220),(0,0,-600),1100)
print('ASSET_COMPLETE',json.dumps(report))
