"""Meridian Garden Habitat. Blender geometry, ImageGen color maps, glTF PBR.
Run: blender --background --python assets/colony_garden/build_colony.py
Model units are 1/1000 game units. Blender Z-up exports as glTF Y-up.
"""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
random.seed(571)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene; scene.render.engine='CYCLES'
scene.cycles.samples=40; scene.cycles.use_denoising=True
scene.unit_settings.system='METRIC'
TAU=math.tau
def rgb(h):
    def linear(x): return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
    return tuple(linear(int(h[i:i+2],16)/255) for i in (0,2,4))
M={}
def material(name,hexcolor,metal=0,rough=.5,emission=0,alpha=1,texture=None):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*rgb(hexcolor),1)
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    if emission:
        bs.inputs['Emission Color'].default_value=(*rgb(hexcolor),1);bs.inputs['Emission Strength'].default_value=emission
    if alpha<1:
        bs.inputs['Alpha'].default_value=alpha;m.surface_render_method='DITHERED';m.use_backface_culling=True
        bs.inputs['IOR'].default_value=1.46;bs.inputs['Coat Weight'].default_value=.35
    if texture:
        tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OUT/'source'/('imagegen_'+texture+'.png')),check_existing=True);tex.image.pack()
        m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    M[name]=m;return m
material('Ivory_ceramic_alloy','e7e2d4',.32,.36,texture='hull')
material('Titanium_structure','64757e',.75,.36)
material('Graphite_recesses','202b32',.5,.62)
material('Champagne_trim','ad9670',.65,.36)
material('Garden_floor_ImageGen','588744',0,.96,texture='garden')
material('Foliage_emerald','3c7141',0,.86,texture='foliage')
material('Foliage_lime','779850',0,.84,texture='foliage')
material('Tree_trunks','65533a',0,.95)
material('Paths_and_plazas','c7bfa8',0,.83)
material('Habitat_windows','ffcf83',.15,.28,1.25)
material('Wayfinding_cyan','79d9df',.2,.28,1.6)
material('Navigation_red','ff6250',.1,.3,2.2)
material('Conservatory_glass','9ac9dc',.12,.14,alpha=.17)
material('Solar_cells','1b334a',.65,.28)
garden_source=next(n.image for n in M['Garden_floor_ImageGen'].node_tree.nodes if n.type=='TEX_IMAGE')
garden_pixels=list(garden_source.pixels[:]);garden_w,garden_h=garden_source.size

# Bake material relief from the hull source into portable normal/roughness maps.
bpy.ops.mesh.primitive_plane_add(size=2);bake_plane=bpy.context.object
bake_plane.data.materials.append(M['Ivory_ceramic_alloy']);mat=bake_plane.active_material;nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF')
source=next(n for n in nt.nodes if n.type=='TEX_IMAGE')
bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.007
nt.links.new(source.outputs['Color'],bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
scene.cycles.samples=1;scene.render.bake.margin=8
target=nt.nodes.new('ShaderNodeTexImage');normal=bpy.data.images.new('hull_normal.png',width=1024,height=1024,alpha=False);normal.colorspace_settings.name='Non-Color';target.image=normal;nt.nodes.active=target
bpy.ops.object.bake(type='NORMAL');normal.filepath_raw=str(OUT/'textures/hull_normal.png');normal.file_format='PNG';normal.save();normal.pack()
nt.nodes.remove(target);nt.nodes.remove(bump)
tex=nt.nodes.new('ShaderNodeTexImage');tex.image=normal;nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
rough=bpy.data.images.new('hull_roughness.png',width=1024,height=1024,alpha=False);rough.colorspace_settings.name='Non-Color'
target=nt.nodes.new('ShaderNodeTexImage');target.image=rough;nt.nodes.active=target
gray=nt.nodes.new('ShaderNodeRGBToBW');nt.links.new(source.outputs['Color'],gray.inputs[0])
mapn=nt.nodes.new('ShaderNodeMapRange');mapn.inputs['To Min'].default_value=.62;mapn.inputs['To Max'].default_value=.31;nt.links.new(gray.outputs[0],mapn.inputs['Value'])
emit=nt.nodes.new('ShaderNodeEmission');nt.links.new(mapn.outputs[0],emit.inputs[0]);output=nt.nodes.get('Material Output');nt.links.new(emit.outputs[0],output.inputs['Surface'])
bpy.ops.object.bake(type='EMIT');rough.filepath_raw=str(OUT/'textures/hull_roughness.png');rough.file_format='PNG';rough.save();rough.pack()
for n in [target,gray,mapn,emit]:nt.nodes.remove(n)
nt.links.new(bs.outputs[0],output.inputs['Surface']);tex=nt.nodes.new('ShaderNodeTexImage');tex.image=rough;nt.links.new(tex.outputs['Color'],bs.inputs['Roughness'])
bpy.data.objects.remove(bake_plane,do_unlink=True)

P={}
for name in ['Habitat_Rings','Civic_Core','Comms_Dish']:
    ob=bpy.data.objects.new(name,None);scene.collection.objects.link(ob);P[name]=ob
P['Comms_Dish'].location.z=30.15
B={}
def mesh(vs,fs,mat='Ivory_ceramic_alloy',group='Habitat_Rings',uv=None,smooth=False):
    key=(group,mat)
    if key not in B:B[key]=[[],[],[],[]]
    verts,faces,uvs,sm=B[key];offset=len(verts);verts.extend(vs)
    for j,f in enumerate(fs):
        faces.append(tuple(offset+i for i in f));sm.append(smooth)
        if uv:uvs.append(uv[j])
        else:
            p=[Vector(vs[i]) for i in f];n=(p[1]-p[0]).cross(p[2]-p[0]);axis=max(range(3),key=lambda a:abs(n[a]));axes=[a for a in range(3) if a!=axis]
            uvs.append([(q[axes[0]]/4,q[axes[1]]/4) for q in p])
def box(p,d,mat='Ivory_ceramic_alloy',group='Habitat_Rings',angle=0):
    vs=[];co,si=math.cos(angle),math.sin(angle)
    for i,j,k in [(-1,-1,-1),(-1,-1,1),(-1,1,1),(-1,1,-1),(1,-1,-1),(1,-1,1),(1,1,1),(1,1,-1)]:
        x,y=i*d[0]/2,j*d[1]/2;vs.append((p[0]+x*co-y*si,p[1]+x*si+y*co,p[2]+k*d[2]/2))
    mesh(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)],mat,group)
def radial(r,a,z,d,mat='Ivory_ceramic_alloy',group='Habitat_Rings'):
    box((r*math.cos(a),r*math.sin(a),z),d,mat,group,a)
def beam(p0,p1,r,mat='Titanium_structure',group='Habitat_Rings',n=8,r1=None):
    p0,p1=Vector(p0),Vector(p1);axis=(p1-p0).normalized();u=axis.cross(Vector((0,0,1)))
    if u.length<.01:u=axis.cross(Vector((0,1,0)))
    u.normalize();v=axis.cross(u);r1=r if r1 is None else r1
    vs=[tuple(p+(u*math.cos(i*TAU/n)+v*math.sin(i*TAU/n))*rr) for p,rr in [(p0,r),(p1,r1)] for i in range(n)]
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh(vs,fs,mat,group,smooth=True)
def sphere(p,r,mat,group='Habitat_Rings',n=10,rings=6,stretch=(1,1,1)):
    vs=[]
    for j in range(rings+1):
        t=math.pi*j/rings
        for i in range(n):
            a=TAU*i/n;vs.append((p[0]+r*math.sin(t)*math.cos(a)*stretch[0],p[1]+r*math.sin(t)*math.sin(a)*stretch[1],p[2]+r*math.cos(t)*stretch[2]))
    fs=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(rings) for i in range(n)]
    uv=[[(i/n,j/rings),((i+1)/n,j/rings),((i+1)/n,(j+1)/rings),(i/n,(j+1)/rings)] for j in range(rings) for i in range(n)] if mat.startswith('Foliage') else None
    mesh(vs,fs,mat,group,uv=uv,smooth=True)
def arc(R,profile,a0=0,a1=TAU,mat='Ivory_ceramic_alloy',group='Habitat_Rings',segments=128,closed=True):
    # CCW profile in radial/Z cross section; outer surfaces point away from material.
    vs=[((R+x)*math.cos(a0+(a1-a0)*i/segments),(R+x)*math.sin(a0+(a1-a0)*i/segments),z) for i in range(segments+1) for x,z in profile]
    N=len(profile);fs=[];uv=[]
    for i in range(segments):
        for j in range(N if closed else N-1):
            k=(j+1)%N;fs.append((i*N+j,(i+1)*N+j,(i+1)*N+k,i*N+k))
            u0=R*(a1-a0)*i/segments/4;u1=R*(a1-a0)*(i+1)/segments/4
            v0=j/(N-1);v1=k/(N-1);uv.append([(u0,v0),(u1,v0),(u1,v1),(u0,v1)])
    if closed and a1-a0<TAU-.001:fs.extend([tuple(range(N-1,-1,-1)),tuple(segments*N+j for j in range(N))]);uv.extend([[(x/4,z/4) for x,z in reversed(profile)],[(x/4,z/4) for x,z in profile]])
    mesh(vs,fs,mat,group,uv,smooth=False)
def tube(R,z,r,mat='Titanium_structure',group='Habitat_Rings',seg=160,a0=0,a1=TAU):
    profile=[(r*math.cos(TAU*i/5),z+r*math.sin(TAU*i/5)) for i in range(5)]
    arc(R,profile,a0,a1,mat,group,seg)
def tree(r,a,z,h,group='Habitat_Rings'):
    x,y=r*math.cos(a),r*math.sin(a)
    beam((x,y,z),(x,y,z+h*.64),h*.055,'Tree_trunks',group,n=5)
    sphere((x,y,z+h*.7),h*.29,random.choice(['Foliage_emerald','Foliage_lime']),group,n=7,rings=4,stretch=(1,.9,1.25))
    sphere((x+h*.15,y-h*.12,z+h*.55),h*.22,'Foliage_emerald',group,n=6,rings=3)

# Pressure hulls are fully closed. Conservatories sit inside the existing toroidal collision envelope.
for R,w,H,bays in [(52,3,2.6,24),(30,1.8,1.8,16)]:
    top=H/2;W=w*.87;rise=1.95 if R==52 else 1.05
    profile=[(-w,-top+.22),(-w+.22,-top),(w-.22,-top),(w,-top+.22),(w,top-.2),(w-.22,top),(-w+.22,top),(-w,top-.2)]
    arc(R,profile,segments=240 if R==52 else 160)
    for z in [-top+.12,top-.12]:
        for rr in [R-w,R+w]:tube(rr,z,.085,seg=192)
    for zz in [-.5,.45] if R==52 else [-.05]:
        for side in [-1,1]:
            rr=R+side*(w+.015)
            for i in range(240 if R==52 else 144):
                a=TAU*i/(240 if R==52 else 144)
                radial(rr,a,zz,(.045,.85 if R==52 else .73,.4),'Graphite_recesses')
                radial(rr+side*.032,a,zz,(.028,.62 if R==52 else .5,.28),'Habitat_windows')
    for i in range(bays):
        a=i*TAU/bays;a0=a+TAU/bays*.135;a1=a+TAU/bays*.865
        # Long planted floors with a real translucent pressure-glass vaulted enclosure.
        arc(R,[(W,top+.025),(-W,top+.025)],a0,a1,'Garden_floor_ImageGen',segments=12,closed=False)
        arch=[(-W*math.cos(math.pi*j/12),top+rise*math.sin(math.pi*j/12)) for j in range(13)]
        arc(R,list(reversed(arch)),a0,a1,'Conservatory_glass',segments=12,closed=False)
        for aa in [a0,a1]:
            vs=[((R+x)*math.cos(aa),(R+x)*math.sin(aa),z) for x,z in arch]
            mesh(vs,[tuple(range(len(vs)))],'Conservatory_glass')
        # Silver structural arches and longitudinal spars catch the actual sun.
        for j in range(7):
            aa=a0+(a1-a0)*j/6
            for k in range(12):
                x,z=arch[k];x2,z2=arch[k+1]
                beam(((R+x)*math.cos(aa),(R+x)*math.sin(aa),z),((R+x2)*math.cos(aa),(R+x2)*math.sin(aa),z2),.038 if j not in (0,6) else .075,'Ivory_ceramic_alloy',n=5)
        for k in [0,3,6,9,12]:
            x,z=arch[k];tube(R+x,z,.026,'Titanium_structure',seg=12,a0=a0,a1=a1)
        # The glazed bays alternate with solid service / airlock modules.
        radial(R,a,top+.12,(w*2,1.35 if R==52 else 1.0,.24))
        for rr in [R-w+.22,R+w-.22]:radial(rr,a,top+.24,(.15,1.8,.12),'Champagne_trim')
        radial(R+w+.05,a,-.1,(.32,1.35,H*.87),'Titanium_structure')
        radial(R+w+.24,a,-.1,(.14,.95,H*.72))
        radial(R+w+.34,a,-.35,(.035,.52,.22),'Wayfinding_cyan')
        for j in range(15 if R==52 else 9):
            for attempt in range(24):
                aa=random.uniform(a0+.01,a1-.01);rr=R+random.uniform(-W*.62,W*.62)
                u=(R*(aa-a0)/4)%1;v=(R+W-rr)/(2*W)
                pixel=(min(garden_h-1,int(v*garden_h))*garden_w+int(u*garden_w))*4
                red,green=garden_pixels[pixel:pixel+2]
                if green>red*1.15 and abs(rr-R)>.3:break
            h=random.uniform(.6,1.17) if R==52 else random.uniform(.42,.66)
            tree(rr,aa,top+.04,h)
        # Curated center promenade and circular gathering plaza, visible through the canopy.
        arc(R,[(.14,top+.044),(-.14,top+.044)],a0,a1,'Paths_and_plazas',segments=12,closed=False)
        aa=(a0+a1)/2;beam((R*math.cos(aa),R*math.sin(aa),top+.045),(R*math.cos(aa),R*math.sin(aa),top+.065),.57,'Paths_and_plazas',n=24)
        if i%3==0:
            radial(R+w-.2,a,top+.48,(.12,.12,.9),'Titanium_structure')
            sphere(((R+w-.2)*math.cos(a),(R+w-.2)*math.sin(a),top+.97),.11,'Navigation_red',n=8,rings=4)

# Eight sealed tram spokes, collars and maintenance piping; no decorative traffic obstacles.
for i in range(8):
    a=i*TAU/8;c,s=math.cos(a),math.sin(a)
    for r0,r1 in [(6.6,28.5),(31.5,49.4)]:
        beam((r0*c,r0*s,0),(r1*c,r1*s,0),.52,n=12)
        for offset in [-.37,.37]:
            beam((r0*c-offset*s,r0*s+offset*c,.24),(r1*c-offset*s,r1*s+offset*c,.24),.085,'Ivory_ceramic_alloy',n=6)
        for j in range(1,6):
            rr=r0+(r1-r0)*j/6;radial(rr,a,0,(.22,1.22,1.15))
        rr=(r0+r1)/2;radial(rr,a,.6,(1.9,.67,.45));radial(rr,a,.84,(1.15,.5,.03),'Wayfinding_cyan')

# Spherical civic atrium and fixed elevator spine. Original pad / berth surfaces are exact.
G='Civic_Core'
sphere((0,0,0),6.98,'Ivory_ceramic_alloy',G,n=72,rings=40)
for z in [-1.45,1.45]:
    rr=math.sqrt(7**2-z*z);tube(rr,z,.13,'Titanium_structure',G)
    for i in range(72):
        a=TAU*i/72;radial(rr+.03,a,z,(.08,.36,.65),'Graphite_recesses',G);radial(rr+.08,a,z,(.04,.23,.51),'Habitat_windows',G)
tube(7.04,0,.2,'Champagne_trim',G)
beam((0,0,-24),(0,0,24),2.6,'Ivory_ceramic_alloy',G,n=32)
for z in [-22,-19.5,-17,-9,-6,6,9,17,19.5,22]:tube(2.65,z,.14,'Titanium_structure',G,seg=64)
for i in range(8):
    a=TAU*i/8
    for z in [-21,-18,-8,8,18,21]:
        radial(2.6,a,z,(.09,.48,1.25),'Graphite_recesses',G);radial(2.67,a,z,(.025,.23,1.05),'Habitat_windows',G)
for sign in [-1,1]:
    y=sign*15
    beam((0,0,y-.25),(0,0,y+.25),5.2,'Ivory_ceramic_alloy',G,n=64)
    for rr in [2.85,4.8,5.15]:tube(rr,y+sign*.26,.035,'Champagne_trim',G,seg=96)
    for i in range(6):
        a=TAU*i/6+math.pi/6
        # Landing markings lie flush; there is no geometry on the actual pads.
        for d in [-.38,.38]:radial(3.5+d,a,y+sign*.26,(.04,.85,.012),'Wayfinding_cyan',G)
    beam((0,0,sign*24),(0,0,sign*29.9),1.0,'Titanium_structure',G,n=16)
    beam((0,0,sign*29.9),(0,0,sign*30.15),1.8,'Ivory_ceramic_alloy',G,n=32)
    # Solar wings stay at the current four-wing locations.
    for sy in [-1,1]:
        beam((0,sy*2.6,sign*19.5),(0,sy*9,sign*19.5),.17,'Titanium_structure',G)
        box((0,sy*13.5,sign*19.5),(14,9,.11),'Solar_cells',G)
        for xx in [-7,7]:box((xx,sy*13.5,sign*19.5),( .12,9,.18),'Ivory_ceramic_alloy',G)
        for k in range(15):box((-7+k,sy*13.5,sign*19.57),(.028,9,.018),'Titanium_structure',G)
        for k in range(10):box((0,sy*(9+k),sign*19.57),(14,.022,.018),'Titanium_structure',G)
    # Game +Z is Blender -Y. Carrier berth center (0, ±12, 6.23).
    z=sign*12
    box((0,0,z),(8.4,6.4,3),'Ivory_ceramic_alloy',G)
    for x in [-3.6,-2.4,-1.2,0,1.2,2.4,3.6]:
        for yy in [-3.22,3.22]:box((x,yy,z),(.7,.04,.45),'Habitat_windows',G)
    box((0,-3.23,z+sign*.72),(7.3,.04,.22),'Champagne_trim',G)
    for x in [-2.2,2.2]:
        box((x,-4.15,z),(.6,1.9,.7),'Titanium_structure',G)
        box((x,-5.23,z),(.7,.26,1.1),'Ivory_ceramic_alloy',G)
        box((x,-5.375,z),(.4,.025,.8),'Wayfinding_cyan',G)
    box((0,-5.165,z-sign*.7),(10,3.93,.16),'Ivory_ceramic_alloy',G)
    for x in [-4.6,4.6]:box((x,-5.2,z-sign*.61),(.06,3.6,.018),'Champagne_trim',G)
    for j in range(1,10):sphere((-4.2-j*4.2,-8.53,z-sign*1.4),.115,'Wayfinding_cyan',G,n=8,rings=4)
    # Dock roof landers occupy x=±2.6, y=±1.5. Keep all added detail off those spots.
    for x in [-4.08,4.08]:box((x,0,z+sign*1.3),(.14,6.3,.4),'Titanium_structure',G)

# Comms assembly is independently animated around the exact original pivot.
G='Comms_Dish'
beam((0,0,0),(0,0,3.0),.16,'Titanium_structure',G,n=12)
# Concave parabolic reflector facing upward, with physical ribs.
vs=[];N=48;RINGS=10
for j in range(RINGS+1):
    r=3.5*j/RINGS
    for i in range(N):a=TAU*i/N;vs.append((r*math.cos(a),r*math.sin(a),2.8+.115*r*r))
fs=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(RINGS) for i in range(N)]
mesh(vs,fs,'Ivory_ceramic_alloy',G,smooth=True)
tube(3.5,2.8+.115*3.5**2,.07,'Titanium_structure',G,seg=64)
for i in range(8):
    a=TAU*i/8
    for j in range(8):
        r0=3.5*j/8;r1=3.5*(j+1)/8
        beam((r0*math.cos(a),r0*math.sin(a),2.77+.115*r0*r0),(r1*math.cos(a),r1*math.sin(a),2.77+.115*r1*r1),.045,'Titanium_structure',G,n=5)
for i in range(3):
    a=TAU*i/3;beam((3.1*math.cos(a),3.1*math.sin(a),3.9),(0,0,5.2),.045,'Titanium_structure',G,n=5)
sphere((0,0,5.2),.19,'Wayfinding_cyan',G,n=12,rings=6)

# Merge by material and moving assembly before export: predictable small draw count.
report={'model_units_per_game_unit':.001,'outer_radius':52,'inner_radius':30,'garden_bays':40,'trees':504,'meshes':[]}
for (group,mat),(vs,fs,uvs,sm) in B.items():
    me=bpy.data.meshes.new(group+'_'+mat);me.from_pydata(vs,[],fs);me.update()
    uv=me.uv_layers.new(name='UVMap')
    for face,coords,smooth in zip(me.polygons,uvs,sm):
        face.use_smooth=smooth
        for i,co in zip(face.loop_indices,coords):uv.data[i].uv=co
    ob=bpy.data.objects.new(group+'_'+mat,me);scene.collection.objects.link(ob);ob.parent=P[group];me.materials.append(M[mat])
    ob['assembly']=group;ob['sharedGardenResource']=True
    report['meshes'].append({'name':ob.name,'triangles':sum(len(f.vertices)-2 for f in me.polygons)})
report['triangles']=sum(m['triangles'] for m in report['meshes']);report['draw_calls']=len(report['meshes'])
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(OUT/'garden-habitat.glb'),export_format='GLB',use_selection=True,export_image_format='AUTO',export_texcoords=True,export_normals=True,export_tangents=False,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
(OUT/'asset-report.json').write_text(json.dumps(report,indent=2)+'\n')

world=bpy.data.worlds.new('Orbital reflected light');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.10,.14,.18,1);world.node_tree.nodes['Background'].inputs[1].default_value=.22;scene.world=world
ld=bpy.data.lights.new('Solar key','SUN');ld.energy=3.5;ld.angle=.009;light=bpy.data.objects.new('Solar key',ld);scene.collection.objects.link(light);light.rotation_euler=Vector((.85,.1,-.45)).to_track_quat('-Z','Y').to_euler()
ld=bpy.data.lights.new('Earth reflected fill','AREA');ld.energy=18000;ld.shape='DISK';ld.size=120;ld.color=(.46,.65,1);light=bpy.data.objects.new('Earth reflected fill',ld);scene.collection.objects.link(light);light.location=(30,-30,-70);light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Habitat portrait');cam=bpy.data.objects.new('Habitat portrait',cd);scene.collection.objects.link(cam);cam.location=(108,-140,104);target=Vector((0,0,1.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cd.lens=43;scene.camera=cam
scene.render.resolution_x=1800;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.cycles.samples=40
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'previews/blender-garden-habitat.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'garden-habitat.blend'))
if '--no-render' not in sys.argv:bpy.ops.render.render(write_still=True)
print(json.dumps({'triangles':report['triangles'],'draw_calls':report['draw_calls'],'glb_bytes':(OUT/'garden-habitat.glb').stat().st_size}))
