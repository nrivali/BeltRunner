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
PALETTE={'light':'E9E3D2','mid':'CFCABA','plate':'89969C','dark':'242C34','structure':'667680','amber':'F2A33A','cyan':'5ED3F0','warm':'FFD9A0','red':'FF5A5A','green':'6BD69A'}
M={};EMIT={'cyan','warm','red','green'}
for k,h in PALETTE.items():
    mat=bpy.data.materials.new('source_'+k);mat.use_nodes=True;nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF')
    mat['kind']=k;mat['metalness']=.64 if k in ('dark','structure') else .34;mat['roughness']=.56 if k=='dark' else .37
    bs.inputs['Metallic'].default_value=mat['metalness'];bs.inputs['Roughness'].default_value=mat['roughness']
    if k not in EMIT and k!='amber':
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=sources['interior' if k in ('dark','structure') else 'hull'];tex.projection='BOX';tex.projection_blend=.035
        coords=nt.nodes.new('ShaderNodeTexCoord');scale=nt.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=1/900
        nt.links.new(coords.outputs['Object'],scale.inputs[0]);nt.links.new(scale.outputs[0],tex.inputs['Vector'])
        tint=nt.nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=.8;tint.inputs[2].default_value=(*rgb(h),1);nt.links.new(tex.outputs['Color'],tint.inputs[1]);nt.links.new(tint.outputs[0],bs.inputs['Base Color'])
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


"""Rounded carrier geometry, executed inside the self-contained Blender builder.
Coordinates below use the game's X-forward / Y-up frame through C().
"""
PROFILE=[[-3290,665,390],[-3090,815,488],[-2800,872,523],[-2300,894,537],[-1500,900,540],[-650,900,540],[0,900,540],[650,897,537],[1300,880,523],[2100,850,498],[2700,813,467],[3200,758,425],[3700,676,355],[4020,545,282],[4280,370,203],[4460,205,126],[4560,96,77],[4600,32,52]]
EXPONENT=2.5
def section(x):
    for a,b in zip(PROFILE,PROFILE[1:]):
        if a[0]<=x<=b[0]:
            t=(x-a[0])/(b[0]-a[0]);return (a[1]*(1-t)+b[1]*t,a[2]*(1-t)+b[2]*t)
    return tuple(PROFILE[0 if x<PROFILE[0][0] else -1][1:])
def power(v):return math.copysign(abs(v)**(2/EXPONENT),v)
def surf(x,a,offset=0):
    w,h=section(x);return (x,(h+offset)*power(math.sin(a)),(w+offset)*power(math.cos(a)))
def shell(name,stations,mat='light',n=64,cy=0,cz=0):
    vs=[(x,cy+h*power(math.sin(i*math.tau/n)),cz+w*power(math.cos(i*math.tau/n))) for x,w,h in stations for i in range(n)]
    fs=[tuple(range(n-1,-1,-1)),tuple((len(stations)-1)*n+i for i in range(n))]
    fs.extend((j*n+i,(j+1)*n+i,(j+1)*n+(i+1)%n,j*n+(i+1)%n) for j in range(len(stations)-1) for i in range(n))
    ob=mesh(name,vs,fs,mat)
    for p in ob.data.polygons:p.use_smooth=p.index>1
    return ob

# A real closed curved hull, with a rounded rectangular tunnel cut all the way through.
body=shell('sculpted pressure hull',PROFILE)
bpy.ops.mesh.primitive_cube_add(location=(0,0,0));cutter=bpy.context.object;cutter.name='temporary hangar cutter';cutter.dimensions=(840,2800,352)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
mod=cutter.modifiers.new('Rounded portal corners','BEVEL');mod.width=42;mod.segments=5;bpy.context.view_layer.objects.active=cutter;bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.context.view_layer.objects.active=body;mod=body.modifiers.new('Full transverse hangar','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
body.data.materials.clear();body.data.materials.append(M['light']);body.data.materials.append(M['dark'])
for p in body.data.polygons:
    p.material_index=1 if p.center.z<-95 else 0
    if abs(p.center.x)<430 and abs(p.center.z)<180:p.use_smooth=False

# Curved armor panels follow the pressure hull; narrow gaps describe the large flowing forms.
def patch(name,x0,x1,a0,a1,mat='light',off=9,nx=8,na=12):
    vs=[surf(x0+(x1-x0)*j/nx,a0+(a1-a0)*i/na,off) for j in range(nx+1) for i in range(na+1)]
    fs=[(j*(na+1)+i,(j+1)*(na+1)+i,(j+1)*(na+1)+i+1,j*(na+1)+i+1) for j in range(nx) for i in range(na)]
    ob=mesh(name,vs,fs,mat)
    for p in ob.data.polygons:p.use_smooth=True
    return ob
for xa,xb in [(-3020,-2370),(-2330,-1530),(-1490,-530),(540,1300),(1340,2140),(2180,2930),(2970,3660),(3700,4260),(4290,4560)]:
    for a0,a1,mat in [(-.13,.56,'light'),(.58,1.56,'light'),(1.58,2.55,'mid'),(2.58,3.27,'light'),(3.30,4.70,'dark'),(4.73,6.12,'dark')]:
        patch('swept hull armor',xa,xb,a0,a1,mat,6,nx=4,na=7)
# Dark thin transverse expansion joints; every collar conforms to the rounded section.
for x in [-3060,-2350,-1510,-505,520,1320,2160,2950,3680,4275]:
    patch('recessed structural seam',x-12,x+12,0,math.tau,'dark',8,nx=1,na=64)
    if x in [-2350,-505,520,2950]:patch('titanium shoulder seam',x-5,x+5,0,math.pi,'structure',11,nx=1,na=64)

def portal_profile(w,h,r,n=6):
    result=[]
    for cx,cy,ang in [(w-r,h-r,0),(-w+r,h-r,math.pi/2),(-w+r,-h+r,math.pi),(w-r,-h+r,math.pi*1.5)]:
        for j in range(n):
            a=ang+j*math.pi/2/(n-1);result.append((cx+r*math.cos(a),cy+r*math.sin(a)))
    return result
def portal_ring(name,w,h,r,iw,ih,ir,z0,z1,mat):
    outer=portal_profile(w,h,r);inner=portal_profile(iw,ih,ir);N=len(outer)
    vs=[(x,y,z) for z,pts in [(z0,outer),(z1,outer),(z0,inner),(z1,inner)] for x,y in pts]
    fs=[]
    for i in range(N):
        j=(i+1)%N;fs.extend([(i,j,N+j,N+i),(2*N+i,3*N+i,3*N+j,2*N+j),(i,2*N+i,2*N+j,j),(N+i,N+j,3*N+j,3*N+i)])
    return mesh(name,vs,fs,mat)
for s in [-1,1]:
    portal_ring('sculpted hangar coaming',490,246,112,420,176,42,s*838,s*905,'dark')
    portal_ring('machined rounded portal lip',474,230,96,439,195,60,s*906,s*920,'structure')
    for x in [-332,332]:box('portal approach marker',(x,216,s*923),(90,7,4),'amber',bevel=1)
    for x in [-466,466]:
        box('recessed field emitter',(x,0,s*921),(18,74,4),'cyan','emissive',2)
    # Gold longitudinal identity stripe runs along each curved cheek.
    for xa,xb in [(-2980,-550),(555,3340)]:
        a=.21 if s==1 else math.pi-.21
        patch('restrained ochre hull stripe',xa,xb,a-.012,a+.012,'amber',12,nx=24,na=1)
    for x in [-2730,-1970,1040,1820,2690,3460]:
        a=.53 if s==1 else math.pi-.53;w,h=section(x);py=(h+13)*power(math.sin(a));pz=(w+13)*power(math.cos(a))
        angle=-s*.6
        box('recessed service window',(x,py,pz),(183,34,15),'dark',rx=angle)
        for dx in [-54,0,54]:box('warm habitation window',(x+dx,py+4,pz+s*5),(40,13,7),'warm','glass',0,angle)
    for x in [-2720,-1970,1510,2700]:
        a=-.18 if s==1 else math.pi+.18;p=surf(x,a,12)
        box('flush service recess',p,(202,89,14),'dark',bevel=9,rx=s*.18)
        for k in range(5):box('service cooling louver',(x-75+k*37,p[1],p[2]+s*9),(12,62,10),'structure',bevel=2,rx=s*.18)

# Low faired bridge flows into the forward shoulder, rather than sitting on a rectangular deck.
bridge=[(1400,65,28),(1590,220,105),(1830,280,144),(2240,300,158),(2540,282,144),(2770,210,105),(2890,75,38)]
shell('faired bridge blister',bridge,'mid',n=40,cy=528)
for s in [-1,1]:
    for x in [1730,1900,2070,2240,2410,2580,2720]:
        w=260 if 1830<=x<=2580 else 170
        box('bridge glazing recess',(x,607,s*w),(152,50,14),'dark',bevel=7,rx=-s*.35)
        box('bridge amber glazing',(x,611,s*(w+7)),(123,27,5),'warm','glass',0,-s*.35)
    box('bridge navigation lamp',(2390,688,s*165),(18,13,18),'red' if s>0 else 'green','emissive',2)
# Streamlined dish pedestal, preserving the proven mining rig's pivot.
vs=[];N=32
for y,rx,rz in [(500,320,240),(630,280,205),(820,155,130),(980,100,96),(995,110,105)]:
    for i in range(N):a=i*math.tau/N;vs.append((-40+rx*math.cos(a),y,rz*math.sin(a)))
fs=[tuple(range(N-1,-1,-1)),tuple(4*N+i for i in range(N))]+[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(4) for i in range(N)]
ob=mesh('faired dish pedestal',vs,fs,'structure')
for p in ob.data.polygons:p.use_smooth=p.index>1
for x in [-1140,-790]:
    for s in [-1,1]:
        p=surf(x,math.pi*.4 if s>0 else math.pi*.6,10)
        box('dorsal heat exchanger',p,(260,30,180),'dark',bevel=14)
        for k in range(6):box('exchanger fin',(x-100+k*40,p[1]+22,p[2]),(10,12,160),'structure',bevel=2)
for x,s in [(-2850,1),(-2850,-1),(3510,1),(3510,-1)]:
    p=surf(x,.65 if s>0 else math.pi-.65,18);box('hull navigation beacon',p,(15,15,15),'red' if s==1 else 'green','emissive',1)

# Three engines in a compact triangular bank, with curved fairings merging into the stern.
ENGINE_CENTERS=[(220,0),(-140,-470),(-140,470)]
for i,(y,z) in enumerate(ENGINE_CENTERS):
    # Hollow curved shroud: separate rounded stations around each circular engine.
    stations=[(-3500,249,224),(-3440,270,224),(-3250,283,203),(-3000,210,155),(-2840,110,75)]
    vs=[];N=40
    for x,outer,inner in stations:
        for r in [outer,inner]:
            for k in range(N):a=k*math.tau/N;vs.append((x,y+r*math.cos(a),z+r*math.sin(a)))
    fs=[]
    for j in range(len(stations)-1):
        for k in range(N):
            q=(k+1)%N
            fs.extend([(j*2*N+k,(j+1)*2*N+k,(j+1)*2*N+q,j*2*N+q),(j*2*N+N+k,j*2*N+N+q,(j+1)*2*N+N+q,(j+1)*2*N+N+k)])
    for j in [0,len(stations)-1]:
        for k in range(N):q=(k+1)%N;fs.append((j*2*N+k,j*2*N+q,j*2*N+N+q,j*2*N+N+k))
    ob=mesh('integrated rounded engine cowl',vs,fs,'mid')
    for p in ob.data.polygons:p.use_smooth=True
    ring('engine bell',(-3415,y,z),233,211,260,'structure',n=40,taper=.76)
    ring('polished nozzle rim',(-3538,y,z),239,215,24,'light',n=48)
    ring('engine luminous annulus',(-3524,y,z),211,198,8,'cyan','emissive',40)
    ring('recessed nozzle liner',(-3414,y,z),188,150,100,'dark',n=32,taper=.81)
    ring('engine throat',(-3348,y,z),148,1,6,'cyan','emissive',32)
    for k in range(8):
        a=k*math.tau/8;beam('radial engine hardware',(-3310,y+228*math.cos(a),z+228*math.sin(a)),(-3505,y+232*math.cos(a),z+232*math.sin(a)),7,'dark')

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
# The off-flank drone docking rail terminates at the existing game attachment points.
for i,x in enumerate((760,850,940)):
    box('drone dock arm',(x,-95,1184),(38,48,632),'structure',bevel=4)
    box('drone docking socket',(x,-80,1500),(66,40,66),'plate',bevel=5)
    box('dock indicator',(x,-57,1500),(22,4,20),'green','emissive',0)
ANCHORS={'hangar_mouth_pos':(0,0,900),'hangar_mouth_neg':(0,0,-900),'pad_pos':(0,-138,525),'pad_neg':(0,-138,-525),'drop_pad':(250,-130,0),'dish_mount':(-40,995,0),'engine_0':(-3480,220,0),'engine_1':(-3480,-140,-470),'engine_2':(-3480,-140,470),'drone_dock_0':(760,-60,1500),'drone_dock_1':(850,-60,1500),'drone_dock_2':(940,-60,1500),'bridge_windows':(2200,610,0)}
anchors={n:empty(n,p) for n,p in ANCHORS.items()}
shape=empty('hull_collision_profile',(0,0,0));shape['definition']=json.dumps({'stations':PROFILE,'exponent':EXPONENT,'engines':[[-3550,-2840,y,z,283] for y,z in ENGINE_CENTERS]})

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
    im=bpy.data.images.new('carrier_'+kind,width=4096 if kind=='basecolor' else 2048,height=4096 if kind=='basecolor' else 2048,alpha=True)
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
assert sum(counts.values())<=65000,counts
def export(name,obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/name),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True,export_cameras=False,export_lights=False)
carrier=[objects[k] for k in ('hull','interior','emissive','glass')]
export('cargo_carrier.glb',carrier+list(anchors.values())+[shape])
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
export('cargo_carrier_assembled.glb',carrier+list(anchors.values())+[shape,objects['dish_yaw'],objects['dish_pitch']]+dishanchors)
report={'triangles':sum(counts[k] for k in ('hull','interior','emissive','glass')),'triangles_with_dish':sum(counts.values()),'triangles_by_mesh':counts,'meshes':['hull','interior','emissive','glass'],'empties':ANCHORS,'atlas_size':4096,'map_sizes':{k:list(im.size) for k,im in maps.items()},'profile':PROFILE,'exponent':EXPONENT,'forward':'+X','up':'+Y','length':8150,'main_hull_width':1800,'main_hull_height':1080,'hangar_clear_x':[-420,420],'hangar_clear_y':[-176,176],'dish':'Separate mining_dish.glb plus complete cargo_carrier_assembled.glb; carrier alone retains original 4-mesh contract.'}
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
for y,z in ENGINE_CENTERS:area('Engine bounce',(-3555,y,z),1e6,240,(.2,.7,1),(-4300,y,z))
data=bpy.data.cameras.new('presentation_camera');cam=bpy.data.objects.new('presentation_camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.clip_start=1;data.clip_end=150000
scene.render.resolution_x=1800;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.cycles.samples=48
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
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cargo_carrier.blend'));print('CARRIER_V3_COMPLETE',flush=True)
