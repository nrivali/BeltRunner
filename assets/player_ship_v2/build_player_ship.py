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
PALETTE={'paint':'ECE8DD','trim':'293039','plate':'73858D','amber':'F2A33A','rubber':'161D2A','glass':'DDD8C8','cyan':'5ED3F0','red':'FF5A5A','green':'6BD69A','warm':'FFD9A0'}
MATS={};groups={};bevels={}
for name,h in PALETTE.items():
    m=bpy.data.materials.new('source_'+name);m.use_nodes=True;MATS[name]=m
    n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*rgb(h),1)
    bs.inputs['Metallic'].default_value=.3;bs.inputs['Roughness'].default_value=.46
    if name in ('paint','trim','plate','amber'):
        tc=n.new('ShaderNodeTexCoord');vm=n.new('ShaderNodeVectorMath');vm.operation='SCALE';vm.inputs[3].default_value=.9
        l.new(tc.outputs['Generated'],vm.inputs[0]);tx=n.new('ShaderNodeTexImage');tx.image=source;tx.projection='BOX';tx.projection_blend=.06;l.new(vm.outputs[0],tx.inputs['Vector'])
        soften=n.new('ShaderNodeMixRGB');soften.blend_type='MIX';soften.inputs[0].default_value=.84;soften.inputs[1].default_value=(1,1,1,1);l.new(tx.outputs['Color'],soften.inputs[2])
        tint=n.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(*((1,1,1) if name=='paint' else rgb(h)),1);l.new(soften.outputs[0],tint.inputs[1]);l.new(tint.outputs[0],bs.inputs['Base Color'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.008;l.new(tx.outputs['Color'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
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
        mod=o.modifiers.new('Crisp bevels','BEVEL');mod.width=bevels[group];mod.segments=2;mod.affect='EDGES';mod.angle_limit=.6
        bpy.ops.object.modifier_apply(modifier=mod.name)
    tri=o.modifiers.new('Triangulate before unwrap','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
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
    size=4096 if key=='basecolor' else 2048
    im=bpy.data.images.new('player_'+key,size,size,alpha=True)
    if key in ('normal','metallic_roughness'):im.colorspace_settings.name='Non-Color'
    maps[key]=im
scene.render.bake.margin=8;scene.render.bake.use_clear=True;scene.cycles.samples=1
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
        elif key=='metallic_roughness':emit.inputs['Color'].default_value=(1,.10 if name=='glass' else .38 if name=='paint' else .48,0 if name in ('glass','rubber') else .28 if name=='paint' else .65,1)
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
        mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*rgb('ECE8DD'),1);nt.links.new(base,mix.inputs[1]);base=mix.outputs[0]
    nt.links.new(base,bs.inputs['Base Color'])
    sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex('metallic_roughness'),sep.inputs['Color']);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    if kind!='glass':
        nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex('normal'),nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
    if kind=='emissive':nt.links.new(tex('emissive'),bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=3
    if kind=='glass':
        bs.inputs['Transmission Weight'].default_value=.9;bs.inputs['Alpha'].default_value=1;bs.inputs['IOR'].default_value=1.45
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
anchors={name:empty(name,p) for name,p in {'dish_mount':MOUNT,'engine_l':(ENGINE_X,ENGINE_Y,-12.87),'engine_r':(-ENGINE_X,ENGINE_Y,-12.87),'nav_l':(12.04,.22,-4.85),'nav_r':(-12.04,.22,-4.85)}.items()}
yaw=empty('mining_dish_yaw',MOUNT);pitch=empty('mining_dish_pitch',(0,-3.8,8.6))
def parent_keep(o,parent):mat=o.matrix_world.copy();o.parent=parent;o.matrix_world=mat
bpy.context.view_layer.update();parent_keep(pitch,yaw)
for name in ('dish_yoke',):parent_keep(objects[name],yaw)
parent_keep(objects['mining_dish'],pitch)
parent_keep(objects['laser_barrel_1'],pitch)
for level in (1,2,3):
    objects[f'laser_barrel_{level}']['attachment_parent']='mining_dish_pitch'
# Barrel variants remain root nodes for interchangeability; consumers attach while preserving world transform.
focus=empty('focus',(0,-3.8,10.77));parent_keep(focus,pitch)
for i in range(6):a=i*math.pi/3;parent_keep(empty('rim_'+str(i),(1.18*math.cos(a),-3.8+1.18*math.sin(a),9.2)),pitch)
for name,o in objects.items():
    o['component']=name
    o['default_visible']=not (name.startswith('wings_') and name!='wings_delta' or any(name==f'{p}_{l}' for p in ('laser_barrel','cargo_pod','engine_nacelle','scanner_dish') for l in (2,3)))
    if name.startswith('wings_'):o['nav_l']=[12.04,.22,4.3 if name=='wings_forward' else -4.85];o['nav_r']=[-12.04,.22,4.3 if name=='wings_forward' else -4.85]
defaults=[name for name,o in objects.items() if o['default_visible']]
variants=[n for n in objects if n not in defaults]
assembled={}
for wing,level in itertools.product(outlines,(1,2,3)):
    active=[n for n in objects if not n.startswith(('wings_','laser_barrel_','cargo_pod_','engine_nacelle_','scanner_dish_'))]+['wings_'+wing]+[f'{p}_{level}' for p in ('laser_barrel','cargo_pod','engine_nacelle','scanner_dish')]
    assembled[f'{wing}_level_{level}']=sum(counts[n] for n in active)
radius=max(v.co.length for o in objects.values() for v in o.data.vertices if o.parent is None)
print('TRIANGLE_COUNTS',json.dumps(counts),flush=True)
assert max(assembled.values())<=24000,assembled
assert radius<=16, radius
report={'triangles_by_mesh':counts,'triangles_all_components':sum(counts.values()),'assembled_triangle_counts':assembled,'max_radius':radius,'forward':'+Z','up':'+Y','dimensions_approx':[24.2,10.3,25.3],'default_components':defaults,'optional_components':variants,'attachments':{n:[o.location.x,o.location.z,-o.location.y] for n,o in anchors.items()},'textures':'4096 basecolor; 2048 normal, metallic_roughness and emissive; Blender baked ImageGen atlas','map_sizes':{k:list(im.size) for k,im in maps.items()}}
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
    if material['name']=='paint':material['pbrMetallicRoughness']['baseColorFactor']=[*rgb('ECE8DD'),1]
payload=json.dumps(doc,separators=(',',':')).encode();payload+=b' '*((-len(payload))%4)
(OUT/'player_ship.glb').write_bytes(struct.pack('<III',0x46546c67,2,20+len(payload)+len(tail))+struct.pack('<II',len(payload),0x4e4f534a)+payload+tail)

# Presentation scene: broad realistic lights and transparent tinted canopy.
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.14,.18,.25,1);bg.inputs['Strength'].default_value=.4
def area(name,p,energy,size,col):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy*.55;data.shape='DISK';data.size=size;data.color=col
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=C(p);o.rotation_euler=(C((0,0,0))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key softbox',(12,24,14),16000,18,(.82,.9,1));area('Warm rim',(-18,14,-10),21000,14,(1,.76,.48));area('Front fill',(-10,8,18),7000,12,(.7,.83,1));area('Engine rim',(8,10,-22),12000,12,(.6,.8,1))
data=bpy.data.cameras.new('presentation_camera');cam=bpy.data.objects.new('presentation_camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO';data.clip_end=1000;data.clip_start=.1
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.cycles.samples=48
def configure(wing='delta',level=1):
    for name,o in objects.items():
        visible=(not name.startswith(('wings_','laser_barrel_','cargo_pod_','engine_nacelle_','scanner_dish_')) or name=='wings_'+wing or name in [f'{p}_{level}' for p in ('laser_barrel','cargo_pod','engine_nacelle','scanner_dish')])
        o.hide_render=not visible;o.hide_set(not visible)
def render(name,p,target=(0,0,0),scale=36):
    cam.location=C(p);cam.rotation_euler=(C(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale;scene.render.filepath=str(OUT/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
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
print('PLAYER_SHIP_V2_COMPLETE',json.dumps(report),flush=True)
