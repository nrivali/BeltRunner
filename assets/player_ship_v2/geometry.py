# Curved pressure hull and modular components. Coordinates: game +Z forward, +Y up.
PROFILE=[(-11.2,2.35,-1.5,1.5),(-10,3.25,-1.9,2.15),(-7,3.95,-2.35,2.7),(-3,4.25,-2.55,2.8),(1,4.1,-2.45,2.7),(5,3.8,-2.05,2.3),(8.5,3.15,-1.55,1.7),(10.8,2.5,-1.15,1.1),(11.8,1.6,-.9,.7),(12.2,.35,-.4,.25)]
def smooth(ob):
    for p in ob.data.polygons:p.use_smooth=True
    return ob
def curved_rows(rows):
    result=[]
    for i in range(len(rows)-1):
        p0=rows[max(0,i-1)];p1=rows[i];p2=rows[i+1];p3=rows[min(len(rows)-1,i+2)]
        for t in [0,.5]:
            vals=[p1[0]+(p2[0]-p1[0])*t]
            for j in [1,2,3]:vals.append(.5*((2*p1[j])+(-p0[j]+p2[j])*t+(2*p0[j]-5*p1[j]+4*p2[j]-p3[j])*t*t+(-p0[j]+3*p1[j]-3*p2[j]+p3[j])*t*t*t))
            vals[1]=max(.025,vals[1]);result.append(vals)
    result.append(rows[-1]);return result
def oval(group,rows,mat='paint',n=40,offset=(0,0,0),cap=True):
    rows=curved_rows(rows)
    vs=[]
    for z,w,b,t in rows:
        for i in range(n):
            a=i*math.tau/n;vs.append((offset[0]+w*math.cos(a),offset[1]+(b+t)/2+(t-b)/2*math.sin(a),offset[2]+z))
    fs=[]
    for k in range(len(rows)-1):
        for i in range(n):fs.append((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i))
    if cap:fs+=[tuple(range(n-1,-1,-1)),tuple(range((len(rows)-1)*n,len(rows)*n))]
    return smooth(mesh(group,vs,fs,mat,0))
def profile(z):
    for a,b in zip(PROFILE,PROFILE[1:]):
        if a[0]<=z<=b[0]:
            f=(z-a[0])/(b[0]-a[0]);return [z]+[a[i]+(b[i]-a[i])*f for i in (1,2,3)]
    return PROFILE[0] if z<PROFILE[0][0] else PROFILE[-1]
def skin_band(group,z0,z1,mat='trim',upper_only=False):
    vs=[];steps=40
    for z in [z0,z1]:
        _,w,b,t=profile(z)
        for i in range(steps+1):
            a=(0 if upper_only else -math.pi)+i*(math.pi if upper_only else math.tau)/steps
            vs.append(((w+.025)*math.cos(a),(b+t)/2+((t-b)/2+.025)*math.sin(a),z))
    return smooth(mesh(group,vs,[(i,i+1,steps+2+i,steps+1+i) for i in range(steps)],mat,0))

body=oval('hull',PROFILE,n=48)
# Real aperture below the canopy, so the cockpit is visible through the glass.
CANOPY=[(-3.05,.10,2.0,2.12),(-2.35,1.75,1.85,3.45),(-.5,2.6,1.65,4.35),(2.3,2.9,1.45,4.65),(5.0,2.7,1.25,4.25),(7.4,2.18,1.05,3.25),(9.0,1.25,.98,1.9),(9.65,.10,1.0,1.1)]
outline=[(-w,z) for z,w,b,t in CANOPY]+[(w,z) for z,w,b,t in reversed(CANOPY)]
cutter=prism('_cutter',outline,8,-.5,'trim',0)
bpy.context.view_layer.objects.active=body
mod=body.modifiers.new('Open cockpit pressure rim','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True);del groups['_cutter'];del bevels['_cutter']
body.data.materials.clear();body.data.materials.append(MATS['paint']);body.data.materials.append(MATS['trim'])
for p in body.data.polygons:p.material_index=1 if p.center.z<-.25 else 0
for z in [-9.5,-6.3]:skin_band('hull_trim',z-.05,z+.05)
skin_band('hull_trim',10.4,10.48)
skin_band('hull_trim',-8.9,-8.64,'amber',True)

# Smooth compound-curved panoramic glazing. Thin frames trace the real seam.
vs=[];N=32;glass_rows=curved_rows(CANOPY)
for z,w,b,t in glass_rows:
    for i in range(N+1):
        a=i*math.pi/N;vs.append((w*math.cos(a),b+(t-b)*math.sin(a),z))
smooth(mesh('canopy',vs,[(k*(N+1)+i,k*(N+1)+i+1,(k+1)*(N+1)+i+1,(k+1)*(N+1)+i) for k in range(len(glass_rows)-1) for i in range(N)],'glass',0))
for sign in [-1,1]:
    for a,b in zip(glass_rows,glass_rows[1:]):beam('cockpit_frame',(sign*a[1],a[2],a[0]),(sign*b[1],b[2],b[0]),.105,'trim',8)
# Narrow rear structural arch keeps the front canopy uninterrupted.
z,w,b,t=CANOPY[2]
for i in range(20):
    a=i*math.pi/20;c=(i+1)*math.pi/20
    beam('cockpit_frame',(w*math.cos(a),b+(t-b)*math.sin(a),z),(w*math.cos(c),b+(t-b)*math.sin(c),z),.065,'plate',6)
box('cockpit',(0,-.35,2.5),(4.8,.24,8.5),'trim',.08)
box('cockpit',(0,.18,1.1),(1.65,.42,1.8),'rubber',.14)
seat=box('cockpit',(0,1.28,.35),(1.65,2.1,.45),'rubber',.16)
box('cockpit',(0,2.32,.32),(.94,.68,.55),'plate',.13)
for s in [-1,1]:
    beam('cockpit',(s*.63,.45,1.9),(s*.63,.8,2.6),.095,'trim',8)
    beam('cockpit',(s*.42,2.05,.63),(s*.46,.6,1.52),.075,'amber',6)
    box('cockpit',(s*1.65,.15,3.0),(.68,.7,3.4),'trim',.1)
    box('emissive',(s*1.65,.54,3.6),(.4,.04,.65),'cyan',.015)
box('cockpit',(0,.67,5.5),(3.35,.45,.9),'trim',.12)
for x in [-.9,0,.9]:box('emissive',(x,.93,5.46),(.63,.035,.48),'cyan',.01)
for x in [-1.35,1.35]:
    box('hull_trim',(x,-.1,11.55),(.64,.46,.22),'trim',.08)
    box('emissive',(x,-.1,11.69),(.43,.23,.045),'warm',.02)

# Recessed-looking technical inserts track the flank curve instead of box pods.
for s in [-1,1]:
    for z in [-4.3,3.8,7.9]:
        _,w,b,t=profile(z);yy=(b+t)/2+.5
        box('hull_trim',(s*(w-.075),yy,z),(.19,.85,1.25),'trim',.12)
        for dz in [-.36,0,.36]:box('hull_trim',(s*(w+.031),yy,z+dz),(.055,.54,.095),'plate',.015)
    _,w,b,t=profile(.1)
    box('hull_trim',(s*(w+.005),.37,.1),(.12,1.4,1.6),'trim',.12)
    box('hull_trim',(s*(w+.075),.42,.1),(.045,1.02,1.19),'plate',.065)
    box('hull_trim',(s*(w+.11),.43,.49),(.03,.18,.24),'amber',.015)

# Closed rounded nacelle noses; two aft-facing hollow engine bells.
ENGINE_X=4.55;ENGINE_Y=1.45
for s in [-1,1]:
    ring('engine_core',(s*ENGINE_X,ENGINE_Y,-11.98),1.7,1.48,1.38,'plate',n=36,ratio=.88,bevel=0)
    ring('engine_core',(s*ENGINE_X,ENGINE_Y,-12.73),1.76,1.51,.14,'trim',n=36,bevel=0)
    ring('emissive',(s*ENGINE_X,ENGINE_Y,-12.82),1.49,1.39,.04,'cyan',n=36,bevel=0)
    ring('emissive',(s*ENGINE_X,ENGINE_Y,-11.37),1.24,.01,.04,'cyan',n=32,bevel=0)
    for i in range(8):
        a=i*math.tau/8
        beam('engine_core',(s*ENGINE_X+1.62*math.cos(a),ENGINE_Y+1.62*math.sin(a),-12.55),(s*ENGINE_X+1.5*math.cos(a),ENGINE_Y+1.5*math.sin(a),-11.38),.065,'trim',6)
for level in [1,2,3]:
    g=f'engine_nacelle_{level}';growth=(level-1)*.09
    for s in [-1,1]:
        oval(g,[(-12.48,1.8,-1.8,1.8),(-11.65,2.08+growth,-1.8,2.12+growth),(-9.5,2.16+growth,-1.65,2.25+growth),(-7.05,1.75,-1.25,1.85),(-5.75,1.02,-.6,1.06),(-5.32,.1,.12,.35)],n=32,offset=(s*ENGINE_X,ENGINE_Y,0),cap=False)
        # Rounded solid pressure cap at the front, no forward-facing exhaust.
        oval(g,[(-5.36,.18,.05,.42),(-5.23,.025,.21,.25)],'plate',n=24,offset=(s*ENGINE_X,ENGINE_Y,0))
        ring(g,(s*ENGINE_X,ENGINE_Y+.08,-10.1),2.19+growth,2.15+growth,.26,'amber',n=32,bevel=0)
        for k in range(level+2):
            box(g,(s*(ENGINE_X+2.09+growth),1.65,-10.85+k*.48),(.09,.62,.18),'trim',.025)

# Sculpted modular winglets: rounded leading edges, a thin tapered trailing edge,
# and the four existing planforms retained for the customization menu.
outlines={'delta':[(3.4,1.0),(5.6,.25),(8.4,-1.2),(11.65,-3.8),(12,-4.85),(11.6,-5.55),(7.0,-4.55),(3.4,-4.0)],
 'swept':[(3.4,1.0),(5.5,-.65),(10.8,-4.2),(12,-4.55),(12,-5.45),(10.4,-5.7),(5.8,-3.8),(3.4,-4)],
 'forward':[(3.4,.7),(7.1,3.5),(11.7,5.1),(12,4.3),(11.8,3.45),(6.3,-2.5),(3.4,-4.0)],
 'twin':[(3.4,0),(8,-2.1),(12,-4.1),(12,-5.6),(7.6,-4.8),(3.4,-4.0)]}
def wing_shape(g,points):
    # Two nested rims add curvature without subdivision modifiers or a thick slab.
    cx=sum(p[0] for p in points)/len(points);cz=sum(p[1] for p in points)/len(points);vs=[];n=len(points)
    for factor,h in [(1,-.45),(1,-.16),(.92,.08),(.65,.16)]:
        vs.extend((cx+(x-cx)*factor,h,cz+(z-cz)*factor) for x,z in points)
    fs=[tuple(range(n-1,-1,-1)),tuple(range(3*n,4*n))]
    for k in range(3):
        for i in range(n):fs.append((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i))
    return smooth(mesh(g,vs,fs,'paint',0))
for name,points in outlines.items():
    g='wings_'+name
    for s in [-1,1]:
        wing_shape(g,[(s*x,z) for x,z in points])
        tipz=4.3 if name=='forward' else -4.85
        # Compact tip protector with a small upward bend.
        beam(g,(s*11.65,-.18,tipz),(s*12.0,.54,tipz-.13),.16,'trim',8)
        box(g,(s*12.04,.22,tipz),(.075,.24,.38),'red' if s>0 else 'green',.012)
        if name=='forward':stripe=[(s*9.7,3.7),(s*10.4,3.96),(s*10.6,3.6),(s*9.9,3.3)]
        else:stripe=[(s*9.2,-3.7),(s*9.8,-4.15),(s*10.15,-4.75),(s*9.48,-4.75)]
        prism(g,stripe,.19,.14,'amber',.01)
        if name=='twin':
            oval(g,[(-7.65,.28,-.4,.35),(-6.7,.46,-.48,.5),(1.5,.4,-.4,.45),(2.45,.08,-.08,.12)],'plate',24,offset=(s*8.9,0,0))

# Cargo capacity grows into the rounded flanks rather than rectangular external bins.
for level in [1,2,3]:
    g=f'cargo_pod_{level}';length=2.7+level*.9
    for s in [-1,1]:
        oval(g,[(-length,.16,-.3,.25),(-length+.7,.65+level*.1,-.65,.65),(1.65,.72+level*.11,-.65,.65),(2.55,.5,-.45,.45),(2.9,.06,-.08,.08)],'paint',24,offset=(s*3.9,-1.08,2.0))
        box(g,(s*(4.65+level*.10),-1.07,2.6),(.045,.32,1.24),'amber',.025)
        box(g,(s*(4.65+level*.10),-.65,1.5),(.05,.15,.4),'plate',.025)

# Short protected chin gimbal: unchanged local aim convention and barrel interfaces.
MOUNT=(0,-3.4,7)
oval('hull_trim',[(5.55,.3,-2.02,-1.7),(6.3,.75,-2.15,-1.45),(7.9,.73,-2.2,-.92),(8.65,.36,-1.82,-.72)],'trim',24)
ring('dish_base',MOUNT,.63,.2,.3,'plate',axis='y',n=24,bevel=0)
box('hull_trim',(0,-2.72,7),(.65,1.10,.4),'trim',.08)
box('dish_yoke',(0,-3.6,7),(.66,.5,.75),'trim',.04)
for s in [-1,1]:
    box('dish_yoke',(s*.91,-3.85,7.8),(.18,.65,2.25),'plate',.045)
    ring('dish_yoke',(s*.9,-3.8,8.6),.23,.06,.15,'amber',n=12,bevel=0)
vs=[];n=32
for r in [.04,.4,.85,1.22]:
    for i in range(n):
        a=math.tau*i/n;vs.append((r*math.cos(a),-3.8+r*math.sin(a),8+.3*(r/1.22)**2))
smooth(mesh('mining_dish',vs,[(k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i) for k in range(3) for i in range(n)],'plate',0))
ring('mining_dish',(0,-3.8,8.32),1.32,1.18,.22,'trim',n=32,bevel=0)
ring('mining_dish',(0,-3.8,8.45),1.25,1.20,.035,'amber',n=32,bevel=0)
for i in range(6):
    a=i*math.pi/3;ring('mining_dish',(1.18*math.cos(a),-3.8+1.18*math.sin(a),8.47),.12,.025,.1,'amber',n=10,bevel=0)
for a in [math.pi/2,math.pi/2+2.094,math.pi/2+4.189]:beam('mining_dish',(1.1*math.cos(a),-3.8+1.1*math.sin(a),8.36),(0,-3.8,9.25),.045,'trim',8)
for level in [1,2,3]:
    g=f'laser_barrel_{level}';length=.38+level*.48
    ring(g,(0,-3.8,9.15+length*.5),.24+level*.035,.14,length,'plate',n=20,bevel=0)
    ring(g,(0,-3.8,9.15+length),.26+level*.035,.16,.1,'trim',n=20,bevel=0)
    ring(g,(0,-3.8,9.21+length),.15,.01,.03,'warm',n=20,bevel=0)

# Move the reflector axis forward within its fork. This leaves room for the full
# upward pitch at either end of the 180-degree yaw arc without a long neck.
for name in ['mining_dish','laser_barrel_1','laser_barrel_2','laser_barrel_3']:
    for ob in groups[name]:ob.location.y-=.7

# Low scanner puck, retaining the three upgrade module slots.
for level in [1,2,3]:
    g=f'scanner_dish_{level}';radius=.56+level*.15;yy=2.98+level*.06
    ring(g,(0,yy,-5.4),radius+.14,.02,.36,'trim',axis='y',n=28,bevel=0)
    ring(g,(0,yy+.24,-5.4),radius+.08,.02,.16,'plate',axis='y',n=28,bevel=0)
    ring(g,(0,yy+.075,-5.4),radius+.151,radius+.12,.08,'cyan',axis='y',n=28,bevel=0)
