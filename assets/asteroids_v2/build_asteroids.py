"""Reproducible Blender asset build. Does not edit or integrate into the game."""
import bpy, bmesh, math, random, json, sys
from pathlib import Path
from mathutils import Vector, Quaternion, noise

OUT = Path(__file__).resolve().parent
for folder in ('textures', 'previews'):
    (OUT / folder).mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.unit_settings.system = 'METRIC'
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'

# Same names, proportions and families as the live ROCK_SHAPES table.
SHAPES = {
    'lumpy':    dict(stretch=(1,1,1), amp=.30, grit=.11, freq=1.3),
    'chunk':    dict(stretch=(1.1,.9,1), amp=.10, grit=.08, freq=1, base='dodeca'),
    'potato':   dict(stretch=(1.45,.85,1), amp=.16, grit=.035, freq=1.1, smooth=True),
    'shard':    dict(stretch=(.55,.6,2.1), amp=.22, grit=.09, freq=1.6),
    'pancake':  dict(stretch=(1.35,.42,1.2), amp=.20, grit=.035, freq=1.4, smooth=True),
    'cratered': dict(stretch=(1,1,1), amp=.10, grit=.04, freq=1, craters=7, smooth=True),
    'cluster':  dict(stretch=(1,1,1), amp=.28, grit=.085, freq=1.3, cluster=True),
    'slab':     dict(stretch=(1.6,.38,1.15), amp=.08, grit=.065, freq=1.2, base='dodeca'),
    'spindle':  dict(stretch=(.5,.5,2.7), amp=.12, grit=.035, freq=1.5, smooth=True),
    'bean':     dict(stretch=(.9,.85,1.9), amp=.10, grit=.04, freq=1.2, smooth=True, pinch=.38),
    'boulder':  dict(stretch=(1.15,.95,1), amp=.08, grit=.06, freq=1, base='dodeca', craters=4),
    'jagged':   dict(stretch=(1,1.2,.9), amp=.34, grit=.14, freq=2.1),
    'wedge':    dict(stretch=(1.4,.75,.9), amp=.06, grit=.055, freq=1, base='octa'),
    'hollow':   dict(stretch=(1,1,1), amp=.26, grit=.08, freq=1.4, smooth=True, hollow=True),
}
# Intentional game colors, including teal platinum and violet voidcrystal.
ORES = {
    'iron':       ('Iron', 'D3DCEC', .29, .94),
    'copper':     ('Copper', 'F39860', .29, .95),
    'gold':       ('Gold', 'F2C94C', .24, .97),
    'platinum':   ('Platinum', '58DDD0', .24, .94),
    'crystal':    ('Voidcrystal', 'B98CFF', .28, .82),
    'cobalt':     ('Cobalt', '578EF1', .28, .92),
    'beryl':      ('Beryl', '39DB85', .30, .83),
    'sulfur':     ('Sulfur glass', 'D4FF3A', .33, .76),
    'emberite':   ('Emberite', 'FF662C', .30, .89),
    'he3':        ('Helium-3 ice', 'ABE8FF', .22, .65),
    'glacite':    ('Glacite', '7FFFD4', .25, .75),
    'nebulite':   ('Nebulite', 'FF7AD9', .27, .88),
    'voidpearl':  ('Void pearl', 'F8F0FF', .20, .88),
    'iridium':    ('Iridium', 'C8FF5A', .25, .96),
    'rhodium':    ('Rhodium', 'FFB36B', .22, .97),
    'obsidian':   ('Obsidian ore', '7A7FA0', .24, .88),
    'darkmatter': ('Dark-matter shard', 'FF2E63', .28, .88),
}

def lin(v):
    return v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4

def rgb(h):
    return tuple(lin(int(h[i:i+2],16)/255) for i in (0,2,4))

def select(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

def modifier(ob, mod):
    select(ob)
    bpy.ops.object.modifier_apply(modifier=mod.name)

def save_image(im, path):
    im.filepath_raw = str(path)
    im.file_format = 'PNG'
    im.save()

def bake_textures():
    """Blender bakes portable albedo, tangent normals and roughness/metalness."""
    bpy.ops.mesh.primitive_plane_add(size=2)
    plane = bpy.context.object
    output = {}
    scene.cycles.samples = 1
    scene.render.bake.margin = 4
    for kind in ('regolith','ore'):
        source = bpy.data.images.load(str(OUT/'source'/f'imagegen_{kind}.png'))
        mat = bpy.data.materials.new('BAKE_SOURCE_'+kind)
        mat.use_nodes = True
        nt = mat.node_tree
        bs = nt.nodes.get('Principled BSDF')
        tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = source
        mul = nt.nodes.new('ShaderNodeVectorMath'); mul.operation = 'SCALE'
        mul.inputs[3].default_value = .40 if kind == 'regolith' else 1.95
        nt.links.new(tex.outputs['Color'],mul.inputs[0])
        nt.links.new(mul.outputs['Vector'],bs.inputs['Base Color'])
        bump = nt.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .70 if kind == 'regolith' else .26
        bump.inputs['Distance'].default_value = .095 if kind == 'regolith' else .018
        nt.links.new(tex.outputs['Color'],bump.inputs['Height'])
        nt.links.new(bump.outputs[0],bs.inputs['Normal'])
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = .02
        ramp.color_ramp.elements[0].color = (.98,.98,.98,1) if kind == 'regolith' else (.90,.90,.90,1)
        ramp.color_ramp.elements[1].position = .7
        ramp.color_ramp.elements[1].color = (.78,.78,.78,1) if kind == 'regolith' else (.65,.65,.65,1)
        nt.links.new(tex.outputs['Color'],ramp.inputs[0])
        nt.links.new(ramp.outputs[0],bs.inputs['Roughness'])
        bs.inputs['Metallic'].default_value = 0 if kind == 'regolith' else 1
        plane.data.materials.clear(); plane.data.materials.append(mat)
        emission = nt.nodes.new('ShaderNodeEmission')
        target = nt.nodes.new('ShaderNodeTexImage')
        out = nt.nodes.get('Material Output')
        maps = {}
        for channel in ('albedo','normal','metalrough'):
            im = bpy.data.images.new(f'{kind}_{channel}',width=1024,height=1024,alpha=False)
            im.colorspace_settings.name = 'sRGB' if channel == 'albedo' else 'Non-Color'
            target.image = im; nt.nodes.active = target
            if channel == 'normal':
                nt.links.new(bs.outputs[0],out.inputs['Surface'])
                bpy.ops.object.bake(type='NORMAL')
            else:
                if channel == 'albedo':
                    nt.links.new(mul.outputs[0],emission.inputs[0])
                else:
                    pack = nt.nodes.new('ShaderNodeCombineColor'); pack.mode = 'RGB'
                    pack.inputs[0].default_value = 1
                    nt.links.new(ramp.outputs[0],pack.inputs[1])
                    pack.inputs[2].default_value = 0 if kind == 'regolith' else 1
                    nt.links.new(pack.outputs[0],emission.inputs[0])
                nt.links.new(emission.outputs[0],out.inputs['Surface'])
                bpy.ops.object.bake(type='EMIT')
            save_image(im,OUT/'textures'/f'{kind}_{channel}.png')
            maps[channel] = im
        output[kind] = maps
        print('TEXTURES',kind,flush=True)
    bpy.data.objects.remove(plane,do_unlink=True)
    return output

def pbr_material(name, maps, tint, roughness=1, metallic=1):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    nt = mat.node_tree; bs = nt.nodes.get('Principled BSDF')
    mat.diffuse_color = (*tint,1); mat.use_fake_user=True
    mat['color_factor'] = list(tint)
    mat['roughness_factor'] = roughness
    mat['metallic_factor'] = metallic
    albedo = nt.nodes.new('ShaderNodeTexImage'); albedo.image = maps['albedo']
    mul = nt.nodes.new('ShaderNodeMixRGB'); mul.blend_type = 'MULTIPLY'
    mul.inputs[0].default_value = 1; mul.inputs[2].default_value = (*tint,1)
    nt.links.new(albedo.outputs[0],mul.inputs[1]); nt.links.new(mul.outputs[0],bs.inputs['Base Color'])
    mr = nt.nodes.new('ShaderNodeTexImage'); mr.image = maps['metalrough']
    split = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(mr.outputs[0],split.inputs[0])
    for channel, value, target in ((1,roughness,'Roughness'),(2,metallic,'Metallic')):
        scale = nt.nodes.new('ShaderNodeMath'); scale.operation = 'MULTIPLY'
        scale.inputs[1].default_value = value
        nt.links.new(split.outputs[channel],scale.inputs[0]); nt.links.new(scale.outputs[0],bs.inputs[target])
    normal = nt.nodes.new('ShaderNodeTexImage'); normal.image = maps['normal']
    normal_map = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(normal.outputs[0],normal_map.inputs['Color']); nt.links.new(normal_map.outputs[0],bs.inputs['Normal'])
    # No emission: all ore identification comes from reflectance and color.
    bs.inputs['Emission Strength'].default_value = 0
    return mat

def N(v, scale=1):
    return noise.noise_vector(v*scale,noise_basis='PERLIN_ORIGINAL').x

def dodecahedron():
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm,subdivisions=1,radius=1)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table(); bm.faces.index_update()
    centers = [f.calc_center_median().normalized() for f in bm.faces]
    faces = []
    for v in bm.verts:
        linked = list(v.link_faces); axis = v.co.normalized()
        u = (centers[linked[0].index]-axis*centers[linked[0].index].dot(axis)).normalized()
        t = axis.cross(u)
        linked.sort(key=lambda f:math.atan2(centers[f.index].dot(t),centers[f.index].dot(u)))
        faces.append([f.index for f in linked])
    bm.free()
    me = bpy.data.meshes.new('dodeca seed'); me.from_pydata(centers,[],faces); me.update()
    return me

def base_object(shape, seed):
    S = SHAPES[shape]
    base = S.get('base','ico')
    if base == 'dodeca':
        me = dodecahedron()
        ob = bpy.data.objects.new(shape,me); scene.collection.objects.link(ob)
    elif base == 'octa':
        vs = [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
        fs = [(0,2,4),(2,1,4),(1,3,4),(3,0,4),(2,0,5),(1,2,5),(3,1,5),(0,3,5)]
        me = bpy.data.meshes.new('octa seed'); me.from_pydata(vs,[],fs); me.update()
        ob = bpy.data.objects.new(shape,me); scene.collection.objects.link(ob)
    else:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5 if S.get('smooth') else 3,radius=1)
        ob = bpy.context.object
    rng = random.Random(seed)
    offset = Vector((seed*.71,seed*1.37,seed*.93))
    craters = []
    for _ in range(S.get('craters',0)):
        direction = Vector(tuple(rng.uniform(-1,1) for _ in range(3))).normalized()
        craters.append((direction,rng.uniform(.26,.51),rng.uniform(.10,.22)))
    for v in ob.data.vertices:
        p = v.co.copy(); d = p.normalized()
        s = 1 + S['amp']*N(p+offset,S['freq'])*1.8 + S['amp']*.45*N(p+offset,3.5)
        s *= 1 - S.get('pinch',0)*(1-d.z*d.z)
        if shape == 'potato': s *= 1+.10*d.x-.05*d.y*d.z
        if shape == 'spindle': s *= .82+.18*abs(d.z)
        if shape == 'shard': s *= 1+.12*d.z
        for axis,w,depth in craters:
            angle = math.acos(max(-1,min(1,d.dot(axis))))
            if angle < w:
                t = 1-angle/w
                s -= depth*(math.sin(t*math.pi/2)**1.4)
            s += .025*math.exp(-((angle-w)/.055)**2)
        v.co = Vector(tuple(p[i]*s*S['stretch'][i] for i in range(3)))
    ob.data.update()
    # Extra vertices subdivide the established silhouette; they do not sphericalize it.
    if not S.get('smooth'):
        sub = ob.modifiers.new('Fracture tessellation','SUBSURF'); sub.subdivision_type='SIMPLE'
        sub.levels = 4 if base in ('dodeca','octa') else 2
        modifier(ob,sub)
    for v in ob.data.vertices:
        p = v.co.copy(); d = p.normalized()
        grit = S['grit']*(1.35*N(p+offset,6.5)+.48*N(p+offset,17)+.20*N(p+offset,37))
        v.co += d*grit
    ob.data.update()
    bm=bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(ob.data); bm.free()
    return ob

def remesh(ob, voxel):
    mod = ob.modifiers.new('Continuous natural geology','REMESH')
    mod.mode='VOXEL'; mod.voxel_size=voxel; mod.use_smooth_shade=True
    modifier(ob,mod)
    smooth = ob.modifiers.new('Eroded junctions','SMOOTH'); smooth.factor=.35; smooth.iterations=2
    modifier(ob,smooth)

def clean_mesh(ob, distance=.000001):
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=distance)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0000001)
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(ob.data);bm.free();ob.data.update()

def construct(shape, variant):
    seed = 137+list(SHAPES).index(shape)*71+variant*1049
    rng = random.Random(seed)
    ob = base_object(shape,seed)
    if shape == 'cluster':
        pieces=[ob]
        for i in range(3):
            lump=base_object('chunk',seed+17+i*43)
            r = rng.uniform(.46,.65)
            direction=Vector((math.cos(i*2.2+.6),math.sin(i*2.2+.6),rng.uniform(-.4,.5))).normalized()
            for v in lump.data.vertices:v.co=v.co*r+direction*.83
            pieces.append(lump)
        bpy.ops.object.select_all(action='DESELECT')
        for p in pieces:p.select_set(True)
        bpy.context.view_layer.objects.active=ob; bpy.ops.object.join()
        remesh(ob,.037)
    if shape == 'hollow':
        # A = a deep navigable pocket; B = a naturally broken through-arch.
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4,radius=1)
        cutter = bpy.context.object
        cutter.scale = (.62,1.02,.62) if variant == 0 else (.48,1.8,.51)
        cutter.location = (0,-.70,.09) if variant == 0 else (.02,0,-.04)
        select(cutter); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        for v in cutter.data.vertices:
            p=v.co.copy(); v.co*=1+.20*N(p+Vector((seed,4,9)),3.2)
        boolean = ob.modifiers.new('Excavated natural cavity','BOOLEAN')
        boolean.operation='DIFFERENCE'; boolean.solver='EXACT'; boolean.object=cutter
        modifier(ob,boolean); bpy.data.objects.remove(cutter,do_unlink=True)
        remesh(ob,.027)
        clean_mesh(ob,.002)
    # Orient into Blender Z-up, retaining the game's X,Y,Z proportions in glTF.
    for v in ob.data.vertices:
        x,y,z=v.co; v.co=(x,-z,y)
    ob.data.update()
    tri=ob.modifiers.new('Portable triangles','TRIANGULATE'); modifier(ob,tri)
    if len(ob.data.polygons)>6500:
        dec=ob.modifiers.new('Near detail budget','DECIMATE'); dec.ratio=6500/len(ob.data.polygons)
        modifier(ob,dec)
    return ob,seed

def finish_surface(ob, seed, stone, ore, threshold=None):
    # A coarse geological field assigns contiguous FLUSH surface triangles to ore.
    # No separate ore node objects, shells, floating faces, or silhouettes are added.
    rng=random.Random(seed+883)
    axis=Vector((rng.uniform(.3,1),rng.uniform(.2,.9),rng.uniform(.3,1))).normalized()
    cross=Vector((-.65,.72,.32)).normalized()
    offset=Vector((seed*.27,seed*.71,seed*.53))
    def score_at(p):
        warp=.36*N(p+offset,2.3)+.12*N(p+offset,6)
        band=abs(math.sin((p.dot(axis)*1.05+warp+.4)*math.pi))
        branch=abs(math.sin((p.dot(cross)*.72+warp+.71)*math.pi))
        return min(band,branch*.9+.17)
    if threshold is None:
        raw=sorted(score_at(f.center) for f in ob.data.polygons)
        threshold=raw[int(len(raw)*.34)]
    # March the continuous ore boundary through each triangle. Splitting at its
    # contour avoids the staircase edges of whole-face material assignment.
    positions=[v.co.copy() for v in ob.data.vertices]
    values=[score_at(p)-threshold for p in positions]
    crossings={}; faces=[]; material_ids=[]
    def crossing(a,b):
        key=tuple(sorted((a,b)))
        if key not in crossings:
            t=values[a]/(values[a]-values[b])
            crossings[key]=len(positions)
            positions.append(positions[a].lerp(positions[b],t))
        return crossings[key]
    for f in ob.data.polygons:
        ids=list(f.vertices)
        for part in (0,1):
            poly=[]
            for a,b in zip(ids,ids[1:]+ids[:1]):
                ina=(values[a]<=0) if part else (values[a]>0)
                inb=(values[b]<=0) if part else (values[b]>0)
                if ina:poly.append(a)
                if ina!=inb:poly.append(crossing(a,b))
            if len(poly)>=3:
                for j in range(1,len(poly)-1):
                    faces.append((poly[0],poly[j],poly[j+1]));material_ids.append(part)
    me=bpy.data.meshes.new(ob.name+'_ore_contours')
    me.from_pydata(positions,[],faces);me.update();ob.data=me
    ob.data.materials.clear(); ob.data.materials.append(stone); ob.data.materials.append(ore)
    uv=ob.data.uv_layers.new(name='SurfaceUV')
    ore_area=0; total_area=0
    for f,material_id in zip(ob.data.polygons,material_ids):
        f.material_index=material_id
        f.use_smooth=True
        ore_area+=f.area*(f.material_index==1); total_area+=f.area
        # World-aligned planar charts: constant texel density, no UV poles.
        n=f.normal; dominant=max(range(3),key=lambda i:abs(n[i]))
        axes=[i for i in range(3) if i!=dominant]
        for li in f.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv=(p[axes[0]]*.78+.17*(seed%7),p[axes[1]]*.78+.13*(seed%11))
    # Split normals only at substantive fractures, rather than faceting every triangle.
    bm=bmesh.new(); bm.from_mesh(ob.data)
    for e in bm.edges:
        if len(e.link_faces)==2:e.smooth=e.calc_face_angle()<.52
    bm.to_mesh(ob.data); bm.free()
    clean_mesh(ob)
    ob['ore_surface_fraction']=round(ore_area/total_area,4)
    ob['ore_threshold']=threshold
    ob['ore_geometry']='flush material regions on continuous rock body'
    return ob

maps=bake_textures()
stone=pbr_material('Barren_Regolith',maps['regolith'],(1,1,1),1,0)
ore_mats={key:pbr_material('Ore_'+key,maps['ore'],rgb(spec[1]),spec[2],spec[3]) for key,spec in ORES.items()}
library=bpy.data.collections.new('ASSET_LIBRARY'); scene.collection.children.link(library)
assets=[]; report=[]
for shape in SHAPES:
    for variant in range(2):
        ob,seed=construct(shape,variant)
        name=f'{shape}_{"AB"[variant]}'
        for coll in list(ob.users_collection):coll.objects.unlink(ob)
        library.objects.link(ob)
        base_mesh=ob.data.copy()
        threshold=None
        for lod,ratio in ((0,1),(1,.23),(2,.05)):
            asset=ob if lod==0 else bpy.data.objects.new(name,base_mesh.copy())
            if lod:library.objects.link(asset)
            if lod:
                dec=asset.modifiers.new('Distance detail reduction','DECIMATE')
                dec.ratio=ratio; modifier(asset,dec)
            finish_surface(asset,seed,stone,ore_mats['iron'],threshold)
            if threshold is None:threshold=asset['ore_threshold']
            asset.name=f'{name}_LOD{lod}'
            asset['shape_family']=shape; asset['variant']='AB'[variant]; asset['lod']=lod
            asset['seed']=seed; asset['base_radius']=1.0
            asset['hollow_type']=('deep_pocket' if variant==0 else 'through_arch') if shape=='hollow' else ''
            asset.data.name=asset.name+'_mesh'
            asset.data.calc_loop_triangles()
            bm=bmesh.new(); bm.from_mesh(asset.data)
            nonmanifold=sum(not e.is_manifold for e in bm.edges); bm.free()
            record=dict(name=asset.name,shape=shape,variant='AB'[variant],lod=lod,seed=seed,
                vertices=len(asset.data.vertices),triangles=len(asset.data.loop_triangles),
                dimensions=[round(float(x),4) for x in asset.dimensions],
                ore_surface_fraction=asset['ore_surface_fraction'],nonmanifold_edges=nonmanifold)
            assets.append(asset); report.append(record)
        print('BUILT',name,report[-3]['triangles'],report[-2]['triangles'],report[-1]['triangles'],flush=True)

# Keep all material definitions in each glTF export using removable tiny templates.
templates=[]
for key,mat in ore_mats.items():
    me=bpy.data.meshes.new('template'); me.from_pydata([(0,0,0),(.001,0,0),(0,.001,0)],[],[(0,1,2)])
    me.uv_layers.new(name='SurfaceUV')
    me.materials.append(mat); ob=bpy.data.objects.new('MATERIAL_TEMPLATE_'+key,me)
    scene.collection.objects.link(ob); templates.append(ob)
for lod in range(3):
    bpy.ops.object.select_all(action='DESELECT')
    chosen=[a for a in assets if a['lod']==lod]
    for i,a in enumerate(chosen):
        a.location=((i%7-3)*6,0,-(i//7)*6)
        a.select_set(True)
    for t in templates:t.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/f'asteroids_lod{lod}.raw.glb'),export_format='GLB',
        use_selection=True,export_extras=True,export_yup=True,export_tangents=True,
        export_materials='EXPORT',export_image_format='AUTO',export_cameras=False,export_lights=False)
    for a in chosen:a.location=(0,0,0)
    print('EXPORTED LOD',lod,flush=True)
for t in templates:bpy.data.objects.remove(t,do_unlink=True)

(OUT/'asset-report.json').write_text(json.dumps(dict(
    generator='Blender '+bpy.app.version_string,shape_count=14,variations_per_shape=2,lod_count=3,
    ore_types={k:dict(label=v[0],color=v[1],roughness=v[2],metallic=v[3]) for k,v in ORES.items()},
    ore_emission=0,texture_resolution=1024,assets=report),indent=2))
for a in assets:
    i=list(SHAPES).index(a['shape_family'])*2+('AB'.index(a['variant']))
    a.location=((i%7-3)*6,(i//7)*6,0)
    a.hide_render=True
    a.hide_set(a['lod']!=0)
for im in bpy.data.images:
    if im.source=='FILE' or im.name in [m.name for pack in maps.values() for m in pack.values()]:
        try:im.pack()
        except RuntimeError:pass
bpy.ops.outliner.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'asteroids.blend'))
print('ASSET BUILD COMPLETE',flush=True)
