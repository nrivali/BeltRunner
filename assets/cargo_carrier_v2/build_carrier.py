import bpy,bmesh,math,random,json
from mathutils import Vector,Quaternion
from pathlib import Path
OUT=Path(__file__).resolve().parent
(OUT/'previews').mkdir(exist_ok=True)
random.seed(83)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.use_denoising=True
bpy.context.preferences.filepaths.save_version=0
def C(v):return Vector((v[0],-v[2],v[1]))
def lin(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
def rgb(h):return tuple(lin(int(h[i:i+2],16)/255) for i in (0,2,4))
sources={k:bpy.data.images.load(str(OUT/'source'/f'imagegen_{k}.png')) for k in ('hull','interior')}
PALETTE={'light':'B4BCCF','mid':'9AA4BF','plate':'828CA9','dark':'303847','structure':'566078','amber':'F2A33A','cyan':'5ED3F0','warm':'FFD9A0','red':'FF5A5A','green':'6BD69A'}
M={};EMIT={'cyan','warm','red','green'}
for k,h in PALETTE.items():
    mat=bpy.data.materials.new('source_'+k);mat.use_nodes=True;nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF')
    mat['kind']=k;mat['metalness']=.28 if k not in EMIT else .2;mat['roughness']=.72 if k=='dark' else .48
    bs.inputs['Metallic'].default_value=mat['metalness'];bs.inputs['Roughness'].default_value=mat['roughness']
    if k not in EMIT and k!='amber':
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=sources['interior' if k in ('dark','structure') else 'hull'];tex.projection='BOX';tex.projection_blend=.035
        coords=nt.nodes.new('ShaderNodeTexCoord');scale=nt.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=1/900
        nt.links.new(coords.outputs['Object'],scale.inputs[0]);nt.links.new(scale.outputs[0],tex.inputs['Vector'])
        tint=nt.nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=.45;tint.inputs[2].default_value=(*rgb(h),1);nt.links.new(tex.outputs['Color'],tint.inputs[1]);nt.links.new(tint.outputs[0],bs.inputs['Base Color'])
        bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.28;bump.inputs['Distance'].default_value=1.4;nt.links.new(tex.outputs['Color'],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
    else:bs.inputs['Base Color'].default_value=(*rgb(h),1)
    if k in EMIT:bs.inputs['Emission Color'].default_value=(*rgb(h),1);bs.inputs['Emission Strength'].default_value=2.5
    M[k]=mat
groups={k:[] for k in ('hull','interior','emissive','glass','dish_yaw','dish_pitch')}
def mesh(name,vs,fs,mat='mid',group='hull'):
    me=bpy.data.meshes.new(name);me.from_pydata([C(v) for v in vs],[],fs);me.update();ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);me.materials.append(M[mat]);groups[group].append(ob);return ob
def box(name,p,d,mat='mid',group='hull',bevel=5,rx=0):
    x,y,z=p;a,b,c=(v/2 for v in d);vs=[(x+i*a,y+j*b,z+k*c) for i,j,k in [(-1,-1,-1),(-1,-1,1),(-1,1,1),(-1,1,-1),(1,-1,-1),(1,-1,1),(1,1,1),(1,1,-1)]]
    ob=mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)],mat,group)
    if bevel:
        bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bevel,min(d)*.22),segments=1,affect='EDGES');bm.to_mesh(ob.data);bm.free()
    if rx:
        pivot=C(p);q=Quaternion(C((1,0,0)),rx)
        for v in ob.data.vertices:v.co=pivot+q@(v.co-pivot)
    return ob
def octagon(w,h,ch):return [(-w,-h+ch),(-w,h-ch),(-w+ch,h),(w-ch,h),(w,h-ch),(w,-h+ch),(w-ch,-h),(-w+ch,-h)]
def loft(name,x0,x1,section0,section1=None,mat='mid',group='hull'):
    section1=section1 or section0;n=len(section0);vs=[(x,y,z) for x,sec in [(x0,section0),(x1,section1)] for z,y in sec];fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)];return mesh(name,vs,fs,mat,group)
def sleeve(x,width,w=900,h=540,ch=140):
    outer=octagon(w,h,ch);inner=octagon(w-24,h-24,ch-10);vs=[]
    for xx,sec in ((x-width/2,outer),(x+width/2,outer),(x-width/2,inner),(x+width/2,inner)):vs.extend((xx,y,z) for z,y in sec)
    fs=[]
    for i in range(8):j=(i+1)%8;fs.extend([(i,j,8+j,8+i),(16+i,24+i,24+j,16+j),(i,16+i,16+j,j),(8+i,8+j,24+j,24+i)])
    return mesh('armored transverse frame',vs,fs,'dark')
def ring(name,p,outer,inner,depth,mat='structure',group='hull',n=32,axis='x',taper=1):
    vs=[]
    for d,r in ((-depth/2,outer),(depth/2,outer*taper),(-depth/2,inner),(depth/2,inner*taper)):
        for i in range(n):a=i*math.tau/n;v=(d,math.cos(a)*r,math.sin(a)*r) if axis=='x' else (math.cos(a)*r,d,math.sin(a)*r);vs.append(tuple(p[j]+v[j] for j in range(3)))
    fs=[]
    for i in range(n):j=(i+1)%n;fs.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    return mesh(name,vs,fs,mat,group)
def beam(name,p,q,r,mat='structure',group='hull',n=8):
    a=C(p);b=C(q);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
    if u.length<.01:u=axis.cross(Vector((0,1,0)))
    u.normalize();v=axis.cross(u);pts=[c+r*(math.cos(i*math.tau/n)*u+math.sin(i*math.tau/n)*v) for c in (a,b) for i in range(n)]
    vs=[(p.x,p.z,-p.y) for p in pts];fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)];return mesh(name,vs,fs,mat,group)
def empty(name,p,parent=None):
    o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.location=C(p);o.empty_display_type='PLAIN_AXES';o.empty_display_size=60
    if parent:o.parent=parent
    return o
def label(text,p,size=30,side=1,group='interior'):
    bpy.ops.object.text_add(location=C(p));o=bpy.context.object;o.data.body=text;o.data.size=size;o.data.align_x='CENTER';o.data.align_y='CENTER';o.data.extrude=.1;o.data.resolution_u=2;o.data.materials.append(M['warm']);o.rotation_euler=(math.pi/2,0,0 if side==1 else math.pi);bpy.ops.object.convert(target='MESH')
    o.vertex_groups.new(name='label_texel_density').add(list(range(len(o.data.vertices))),1,'REPLACE')
    groups[group].append(o);return o

# Beveled pressure hull: broad flat panels and a full-width transverse hangar void.
core=octagon(876,522,128)
loft('aft pressure hull',-3290,-420,core,mat='plate');loft('forward pressure hull',420,3700,core,mat='plate')
upper=[(-876,176),(-876,394),(-748,522),(748,522),(876,394),(876,176)]
loft('hangar roof shell',-420,420,upper,mat='plate');loft('hangar keel shell',-420,420,[(z,-y) for z,y in reversed(upper)],mat='plate')
loft('tapered prow',3700,4600,core,octagon(36,52,14),'light')
for x,w in [(-3170,130),(-2280,92),(-520,120),(650,110),(2760,96),(3630,140)]:
    sleeve(x,w)
    for s in (-1,1):
        box('frame face rail',(x,0,s*892),(w*.44,720,12),'structure',bevel=3)
        for y in (-325,325):box('frame armor clamp',(x,y,s*891),(w+26,66,18),'light')
    for s in (-1,1):box('roof frame cap',(x,s*532,0),(w*.5,16,1430),'structure')
# Large side panels organized around the ribs and the hangar opening.
sections=[(-3100,-2340),(-2220,-590),(-450,420),(725,2695),(2830,3550)]
for x0,x1 in sections:
    for s in (-1,1):
        for y in (-143,143):
            if x1<=-420 or x0>=420:box('horizontal armor rail',((x0+x1)/2,y,s*897),(x1-x0-8,19,6),'light',bevel=1)
    n=max(1,round((x1-x0)/480));step=(x1-x0)/n
    for i in range(n):
        x=x0+(i+.5)*step
        for s in (-1,1):
            for y in (-272,272):box('side armor panel',(x,y,s*883),(step-12,225,22),'light' if i%3 else 'mid')
            if x1<=-420 or x0>=420:
                box('broad middle plate',(x,0,s*883),(step-12,300,22),'mid')
                box('maintenance hatch',(x-step*.21,0,s*897),(step*.25,104,5),'plate',bevel=1)
            for sy in (-1,1):
                # Warm window strips sit on the chamfered shoulder, clear of the portal.
                angle=-s*sy*math.pi/4
                box('window recess',(x,sy*469,s*824),(step-38,55,20),'dark',bevel=3,rx=angle)
                for j in range(5):box('warm service window',(x+(j-2)*(step-54)/5,sy*474,s*829),((step-72)/5-8,21,7),'warm','glass',0,angle)
        for sz in (-1,1):
            for y in (-1,1):box('roof armor tile',(x,y*529,sz*395),(step-13,22,676),'light' if i%2 else 'mid')
        for s in (-1,1):
            beam('shoulder conduit',(x-step*.42,549,s*665),(x+step*.42,549,s*665),9,'dark')
            for dx in (-step*.38,step*.38):box('conduit cleat',(x+dx,543,s*665),(28,24,43),'structure',bevel=2)
for x in (-2860,-1820,-1100,2120,3220):
    box('vent plinth',(x,554,0),(240,50,240),'dark')
    for j in range(6):box('vent cooling fin',(x-94+j*38,585,0),(15,16,210),'structure',bevel=1)
# Prow plating lies directly on each sloped face.
for s in (-1,1):
    for t0,t1 in ((.03,.34),(.355,.68),(.695,.96)):
        xa=3700+900*t0;xb=3700+900*t1
        za=(878-840*t0)*s;zb=(878-840*t1)*s;ya=394-356*t0;yb=394-356*t1
        for sy in (-1,1):
            mesh('prow cheek armor',[(xa,sy*8,za),(xb,sy*8,zb),(xb,sy*yb,zb),(xa,sy*ya,za)],[(0,1,2,3)],'mid')
        beam('prow structural edge',(xa,ya,za),(xb,yb,zb),8,'dark')
    box('nose position light',(4578,23,s*48),(32,10,7),'warm','emissive',0)
for y in (-1,1):beam('prow center ridge',(3740,y*512,0),(4560,y*68,0),8,'structure')
# Portal frame and four emitters per flank. The clear passage remains x +/-420, y +/-176.
for s in (-1,1):
    for y in (-202,202):box('portal lintel',(0,y,s*872),(952,52,56),'dark',bevel=10);box('portal silver trim',(0,y,s*896),(926,24,6),'light',bevel=1)
    for x in (-447,447):box('portal jamb',(x,0,s*872),(54,352,56),'dark',bevel=7);box('jamb trim',(x,0,s*897),(24,322,5),'light',bevel=1)
    for x in (-463,463):
        for y in (-212,212):
            box('field emitter housing',(x,y,s*877),(75,94,46),'structure',bevel=10)
            box('field cyan lens',(x,y,s*899),(27,54,3),'cyan','emissive',0)
    for x in (-325,325):box('portal amber marker',(x,231,s*894),(90,7,5),'amber',bevel=0)
# Fully modeled hangar with thin panel layers, recessed deck lanes, pads and workstations.
box('hangar floor',(0,-163,0),(840,26,1800),'dark','interior',0)
box('ceiling skin',(0,183,0),(840,14,1800),'dark','interior',0)
for z in range(-780,781,260):
    for x in (-265,0,265):box('deck access tile',(x,-148,z),(252,4,244),'plate','interior',0)
    for s in (-1,1):
        box('wall service panel',(s*413,6,z),(14,300,242),'structure','interior',2)
        box('wall vertical frame',(s*402,0,z-126),(22,338,18),'dark','interior',2)
        box('wall utility inset',(s*402,5,z),(11,158,120),'dark','interior',1)
        box('wall access console',(s*390,-28,z),(18,70,70),'plate','interior',2)
        box('console luminous screen',(s*379,-15,z),(3,21,40),'cyan','emissive',0)
        beam('wall service pipe',(s*386,-97,z-110),(s*386,92,z-110),4,'structure','interior')
        box('ceiling light housing',(s*264,164,z),(152,18,82),'structure','interior',3)
        box('ceiling light',(s*264,154,z),(124,3,54),'warm','emissive',0)
    for x in (-360,360):beam('ceiling conduit',(x,155,z-118),(x,155,z+118),5,'structure','interior')
for z in (-525,525):
    box('landing pad',(0,-145,z),(300,14,300),'dark','interior',3)
    for x in (-146,146):box('pad edge',(x,-136,z),(8,4,292),'cyan','emissive',0)
    for dz in (-146,146):box('pad edge',(0,-136,z+dz),(292,4,8),'cyan','emissive',0)
    for x in (-30,30):box('landing alignment',(x,-137,z),(16,2,75),'amber','interior',0)
box('cargo drop platform',(250,-137,0),(230,14,230),'plate','interior',3)
for z in (-110,110):box('drop safety edge',(250,-129,z),(218,2,7),'amber','interior',0)
for x in (142,358):box('drop safety edge',(x,-129,0),(7,2,218),'amber','interior',0)
box('cargo sign',(0,130,0),(230,61,12),'dark','interior',2)
for s in (-1,1):label('CARGO DROP',(0,130,s*7),25,s,'emissive')
# Raised bridge with an angled front, stepped roof, exposed side equipment and rear mast.
box('bridge foundation',(900,560,0),(1250,78,1010),'dark',bevel=14)
bridge0=octagon(438,118,30);loft('bridge wheelhouse',300,1500,[(z,y+683) for z,y in bridge0],[(z*.84,y*.86+683) for z,y in bridge0],'light')
for s in (-1,1):
    box('bridge window recess',(900,746,s*412),(1120,63,24),'dark',bevel=5)
    for x in range(425,1400,170):box('bridge warm glass',(x,750,s*426),(149,36,4),'warm','glass',0)
    box('bridge lower maintenance strip',(890,634,s*433),(1060,25,15),'structure',bevel=3)
    for x in (450,730,1010,1290):box('bridge service hatch',(x,667,s*432),(122,75,9),'plate',bevel=2)
box('bridge roof',(875,817,0),(1240,35,913),'mid',bevel=12)
box('bridge top equipment',(680,861,0),(420,55,330),'structure',bevel=10)
for z in (-245,245):box('roof utility rail',(910,844,z),(740,16,18),'dark')
for z in (-250,-125,0,125,250):box('forward bridge window',(1504,742,z),(6,35,107),'warm','glass',0)
for x,z in ((410,-378),(1350,378)):
    box('bridge beacon foot',(x,847,z),(40,30,40),'structure')
    box('bridge beacon',(x,871,z),(18,20,18),'cyan','emissive',0)
for x,z in ((-1200,-270),(-1040,230),(-620,-330)):
    box('roof machinery foundation',(x,553,z),(290,48,270),'dark')
    box('roof machinery',(x,640,z),(258,145,244),'mid',bevel=18)
    for dz in (-116,116):box('machinery rib',(x,641,z+dz),(27,160,18),'structure')
box('mast platform',(-40,557,0),(420,70,380),'structure',bevel=10)
box('mast column',(-40,786,0),(132,390,132),'plate',bevel=8)
for z in (-140,140):beam('mast diagonal brace',(-180,581,z),(-40,951,z*.3),24,'dark')
box('mast cap',(-40,980,0),(200,30,200),'light')
for x,z,h in ((-360,-220,1180),(-240,240,1080)):
    beam('communications antenna',(x,540,z),(x,h,z),7,'structure');box('antenna beacon',(x,h+10,z),(18,18,18),'red','emissive',0)
# Engine bank: three hollow bells at the required attachment coordinates.
loft('stern engine cradle',-3298,-3160,octagon(872,500,112),mat='dark')
for i,z in enumerate((-540,0,540)):
    ring('engine armored collar',(-3272,0,z),253,215,100,'dark',n=32)
    ring('engine bell',(-3415,0,z),238,213,270,'structure',n=32,taper=.76)
    ring('engine silver lip',(-3538,0,z),240,216,24,'light',n=40)
    ring('engine luminous annulus',(-3524,0,z),214,199,8,'cyan','emissive',40)
    ring('engine inner nozzle',(-3414,0,z),190,151,100,'dark',n=32,taper=.81)
    ring('engine throat',(-3348,0,z),150,1,6,'cyan','emissive',32)
    for k in range(8):
        a=k*math.tau/8;beam('engine mounting strut',(-3275,math.cos(a)*220,z+math.sin(a)*220),(-3480,math.cos(a)*233,z+math.sin(a)*233),10,'dark')
for x in (-3050,3300):
    for s in (-1,1):box('hull navigation beacon',(x,554,s*610),(22,30,22),'red' if s==1 else 'green','emissive',0)
# The off-flank drone docking rail terminates at the existing game attachment points.
for i,x in enumerate((760,850,940)):
    box('drone dock arm',(x,-95,1184),(38,48,632),'structure',bevel=4)
    box('drone docking socket',(x,-80,1500),(66,40,66),'plate',bevel=5)
    box('dock indicator',(x,-57,1500),(22,4,20),'green','emissive',0)
ANCHORS={'hangar_mouth_pos':(0,0,900),'hangar_mouth_neg':(0,0,-900),'pad_pos':(0,-138,525),'pad_neg':(0,-138,-525),'drop_pad':(250,-130,0),'dish_mount':(-40,995,0),'engine_0':(-3480,0,-540),'engine_1':(-3480,0,0),'engine_2':(-3480,0,540),'drone_dock_0':(760,-60,1500),'drone_dock_1':(850,-60,1500),'drone_dock_2':(940,-60,1500),'bridge_windows':(900,734,0)}
anchors={n:empty(n,p) for n,p in ANCHORS.items()}

# Separate articulated dish, assembled for the presentation but exported independently for game rigging.
ring('dish yaw ring',(-40,1020,0),135,104,50,'dark','dish_yaw',32,'y')
box('dish pivot housing',(-40,1095,0),(182,110,170),'plate','dish_yaw',12)
for z in (-138,138):beam('dish yoke',(-40,1080,z),(-70,1350,z),22,'structure','dish_yaw')
center=Vector((-70,1350,0));direction=Vector((.83,.55,0)).normalized();u=Vector((0,0,1));v=direction.cross(u).normalized();R=265;n=40
def dishpoint(r,a,back=0):return tuple(center+direction*(r*r/820-back)+r*(math.cos(a)*u+math.sin(a)*v))
vs=[dishpoint(r,i*math.tau/n) for r in (65,132,198,R) for i in range(n)]+[tuple(center)];fs=[(4*n,i,(i+1)%n) for i in range(n)]
for j in range(3):
    for i in range(n):k=(i+1)%n;fs.append((j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i))
mesh('parabolic reflector',vs,fs,'light','dish_pitch')
for i in range(n):
    a=i*math.tau/n;b=(i+1)*math.tau/n;beam('dish rim',dishpoint(R,a),dishpoint(R,b),6,'structure','dish_pitch',6)
for i in range(10):
    a=i*math.tau/10
    for r0,r1 in ((30,110),(110,190),(190,R)):beam('reflector rear rib',dishpoint(r0,a,12),dishpoint(r1,a,12),5,'dark','dish_pitch',6)
focus=tuple(center+direction*190)
for a in (0,math.tau/3,math.tau*2/3):beam('focus support',dishpoint(R*.89,a),focus,5,'dark','dish_pitch',6)
box('focus emitter',focus,(22,22,22),'cyan','dish_pitch',0)
rimpositions=[]
for i in range(6):
    p=dishpoint(R,i*math.tau/6);rimpositions.append(p);box('rim laser emitter',p,(15,15,15),'warm','dish_pitch',0)

# Consolidate the carrier to four draw groups; the optional dish retains its two moving components.
objects={}
for name,items in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for ob in items:ob.select_set(True)
    bpy.context.view_layer.objects.active=items[0];bpy.ops.object.join();ob=bpy.context.object;ob.name=name;ob.data.name=name
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();objects[name]=ob
print('GEOMETRY_READY',sum(len(o.data.polygons) for o in objects.values()),flush=True)
# A single, non-overlapping UV atlas for the complete kit, with extra area for close-view interior details.
bpy.ops.object.select_all(action='DESELECT')
for ob in objects.values():
    ob.select_set(True)
    # Converted text can carry a UV layer. Remove it so baking, rendering and
    # glTF all use the same single atlas rather than different active layers.
    while ob.data.uv_layers:ob.data.uv_layers.remove(ob.data.uv_layers[0])
    ob.data.uv_layers.new(name='UVMap')
# Reserve additional texel density for the fly-through interior before packing.
for vert in objects['interior'].data.vertices:vert.co*=3.5
# Thin pad strips and navigation beacons need several pixels across their faces.
for vert in objects['emissive'].data.vertices:vert.co*=6
letter_group=objects['emissive'].vertex_groups['label_texel_density'].index
letter_indices=[v.index for v in objects['emissive'].data.vertices if any(g.group==letter_group for g in v.groups)]
# Fine lettering needs a minimum useful footprint in the shared 2K texture.
for i in letter_indices:objects['emissive'].data.vertices[i].co*=2
bpy.context.view_layer.objects.active=objects['hull'];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.002,area_weight=.55,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
for vert in objects['interior'].data.vertices:vert.co/=3.5
for vert in objects['emissive'].data.vertices:vert.co/=6
for i in letter_indices:
    vert=objects['emissive'].data.vertices[i];vert.co/=2
    assert abs(vert.co.x)<115 and abs(vert.co.y)<8 and 100<vert.co.z<160
for ob in objects.values():ob.data.update()
print('UV_READY',flush=True)
maps={}
for kind in ('basecolor','metallic_roughness','normal','emissive'):
    im=bpy.data.images.new('carrier_'+kind,width=2048,height=2048,alpha=True)
    if kind in ('normal','metallic_roughness'):im.colorspace_settings.name='Non-Color'
    maps[kind]=im
records=[]
for name,mat in M.items():
    nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF');out=nt.nodes.get('Material Output');emit=nt.nodes.new('ShaderNodeEmission');target=nt.nodes.new('ShaderNodeTexImage')
    base=bs.inputs['Base Color'].links[0].from_socket if bs.inputs['Base Color'].is_linked else None
    records.append((name,mat,nt,bs,out,emit,target,base))
scene.render.bake.margin=3;scene.render.bake.use_clear=False
for kind in ('basecolor','metallic_roughness','emissive','normal'):
    for name,mat,nt,bs,out,emit,target,base in records:
        target.image=maps[kind];nt.nodes.active=target
        for link in list(emit.inputs[0].links):nt.links.remove(link)
        if kind=='normal':nt.links.new(bs.outputs[0],out.inputs['Surface'])
        else:
            if kind=='basecolor' and base:nt.links.new(base,emit.inputs[0])
            elif kind=='basecolor':emit.inputs[0].default_value=bs.inputs['Base Color'].default_value
            elif kind=='metallic_roughness':emit.inputs[0].default_value=(1,mat['roughness'],mat['metalness'],1)
            else:emit.inputs[0].default_value=(*rgb(PALETTE[name]),1) if name in EMIT else (0,0,0,1)
            nt.links.new(emit.outputs[0],out.inputs['Surface'])
    bpy.ops.object.bake(type='NORMAL' if kind=='normal' else 'EMIT')
    im=maps[kind];im.filepath_raw=str(OUT/'textures'/f'carrier_{kind}.png');im.file_format='PNG';im.save();im.pack();print('BAKED',kind,flush=True)
finalmats={}
for name in ('hull','interior','emissive','glass'):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF')
    def tex(k):o=nt.nodes.new('ShaderNodeTexImage');o.image=maps[k];return o.outputs['Color']
    nt.links.new(tex('basecolor'),bs.inputs['Base Color']);sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex('metallic_roughness'),sep.inputs['Color']);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex('normal'),nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
    if name in ('emissive','glass'):nt.links.new(tex('emissive'),bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=2.5
    finalmats[name]=mat
counts={}
for name,ob in objects.items():
    old=[ob.data.materials[p.material_index]['kind'] for p in ob.data.polygons];ob.data.materials.clear()
    if name.startswith('dish_'):
        for mat in finalmats.values():ob.data.materials.append(mat)
        for p,k in zip(ob.data.polygons,old):p.material_index=2 if k in EMIT else 0
    else:ob.data.materials.append(finalmats[name])
    bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('Triangulated','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name);counts[name]=len(ob.data.polygons)
assert sum(counts.values())<=40000,counts
def export(name,obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/name),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True,export_cameras=False,export_lights=False)
carrier=[objects[k] for k in ('hull','interior','emissive','glass')]
export('cargo_carrier.glb',carrier+list(anchors.values()))
# Set dish origins to its actual axes and retain its assembled world pose in the studio.
for name,p in [('dish_yaw',(-40,995,0)),('dish_pitch',tuple(center))]:
    ob=objects[name];pivot=C(p)
    for vert in ob.data.vertices:vert.co-=pivot
    ob.location=pivot
scene.view_layers[0].update();pitch=objects['dish_pitch'];world=pitch.matrix_world.copy();pitch.parent=objects['dish_yaw'];pitch.matrix_world=world
dishanchors=[]
for name,p in [('focus',focus)]+[(f'rim_{i}',p) for i,p in enumerate(rimpositions)]:
    ob=empty(name,p);ob.parent=pitch;ob.location=C(p)-C(center);dishanchors.append(ob)
export('mining_dish.glb',[objects['dish_yaw'],objects['dish_pitch']]+dishanchors)
export('cargo_carrier_assembled.glb',carrier+list(anchors.values())+[objects['dish_yaw'],objects['dish_pitch']]+dishanchors)
report={'triangles':sum(counts[k] for k in ('hull','interior','emissive','glass')),'triangles_with_dish':sum(counts.values()),'triangles_by_mesh':counts,'meshes':['hull','interior','emissive','glass'],'empties':ANCHORS,'atlas_size':2048,'forward':'+X','up':'+Y','length':8150,'main_hull_width':1800,'main_hull_height':1080,'hangar_clear_x':[-420,420],'hangar_clear_y':[-176,176],'dish':'Separate mining_dish.glb plus complete cargo_carrier_assembled.glb; carrier alone retains original 4-mesh contract.'}
(OUT/'asset_report.json').write_text(json.dumps(report,indent=2));print('EXPORTED',json.dumps(counts),flush=True)

# Realistic Cycles softbox lighting. Lights/cameras belong to the studio only.
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.11,.14,.20,1);bg.inputs[1].default_value=.4
def area(name,p,power,size,color,target=(0,0,0)):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color;ob=bpy.data.objects.new(name,d);scene.collection.objects.link(ob);ob.location=C(p);ob.rotation_euler=(C(target)-ob.location).to_track_quat('-Z','Y').to_euler()
area('Broad neutral key',(1800,7500,4500),1.25e9,6500,(1,.94,.86))
area('Cool rear rim',(-5200,3600,-5500),1.55e9,5500,(.62,.77,1))
area('Front fill',(5000,1800,8000),4.4e8,5000,(.80,.88,1))
for z in (-660,0,660):
    for x in (-260,260):area('Hangar ceiling luminaire',(x,146,z),140000,130,(1,.83,.61),(x,-150,z))
for z in (-540,0,540):area('Engine bounce',(-3555,0,z),1e6,240,(.2,.7,1),(-4300,0,z))
data=bpy.data.cameras.new('presentation_camera');cam=bpy.data.objects.new('presentation_camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.clip_start=1;data.clip_end=150000
scene.render.resolution_x=2000;scene.render.resolution_y=1125;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.cycles.samples=96
def render(name,pos,target,scale=9900,persp=False,lens=26):
    cam.location=C(pos);cam.rotation_euler=(C(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.type='PERSP' if persp else 'ORTHO';data.ortho_scale=scale;data.lens=lens
    temp=OUT/'previews'/(name+'.tmp.png');scene.render.filepath=str(temp);bpy.ops.render.render(write_still=True);temp.replace(OUT/'previews'/(name+'.png'));print('RENDERED',name,flush=True)
render('preview_front',(8300,3800,15100),(420,310,0),10050)
render('preview_rear',(-9500,3500,13000),(150,250,0),9950)
render('preview_hangar',(0,0,1180),(0,-3,-600),persp=True,lens=23)
render('preview_profile',(400,2300,17000),(450,320,0),9900)
cam.location=C((8300,3800,15100));cam.rotation_euler=(C((420,310,0))-cam.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=10050
for im in sources.values():im.pack()
for screen in bpy.data.screens:
    for area_ in screen.areas:
        if area_.type=='VIEW_3D':area_.spaces.active.clip_end=150000;area_.spaces.active.region_3d.view_distance=10500;area_.spaces.active.region_3d.view_location=C((400,300,0))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cargo_carrier.blend'));print('CARRIER_V2_COMPLETE',flush=True)
