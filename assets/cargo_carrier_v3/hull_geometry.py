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
