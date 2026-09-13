"""Render the actual textured assets with Cycles sunlight and reflected fill."""
import bpy, math, random, sys
from mathutils import Vector
from pathlib import Path
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'asteroids.blend'))
scene=bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.samples=48; scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.15,.19,.24,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.24
scene.render.film_transparent=False
assets={o.name:o for o in bpy.data.collections['ASSET_LIBRARY'].objects}
for ob in assets.values():ob.hide_render=True; ob.hide_set(True)
preview=bpy.data.collections.new('PREVIEW_STAGE'); scene.collection.children.link(preview)
def stage(ob):
    for c in list(ob.users_collection):c.objects.unlink(ob)
    preview.objects.link(ob)
    return ob
def look(ob,p):ob.rotation_euler=(Vector(p)-ob.location).to_track_quat('-Z','Y').to_euler()
def lamp(name,kind,p,energy,color,size):
    data=bpy.data.lights.new(name,kind); data.energy=energy; data.color=color
    if kind=='AREA':data.shape='DISK';data.size=size
    else:data.angle=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=p;look(ob,(0,0,0));return ob
sun=lamp('Distant warm sunlight','SUN',(-8,2,12),3.5,(1,.91,.78),.07)
fill=lamp('Broad cool reflected light','AREA',(4,-2,8),1800,(.60,.76,1),10)
edge=lamp('Soft reflected rim','AREA',(-4,6,4),1400,(1,.95,.85),9)
bpy.ops.object.camera_add(location=(0,0,35));camera=bpy.context.object
camera.rotation_euler=(0,0,0);camera.data.type='ORTHO';scene.camera=camera
text_mat=bpy.data.materials.new('Preview typography');text_mat.use_nodes=True
bs=text_mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.65,.77,.85,1)
bs.inputs['Emission Color'].default_value=(.65,.77,.85,1);bs.inputs['Emission Strength'].default_value=.7
def text(body,p,size=.22):
    bpy.ops.object.text_add(location=p);ob=stage(bpy.context.object)
    ob.data.body=body;ob.data.align_x='CENTER';ob.data.align_y='CENTER';ob.data.size=size
    ob.data.space_character=1.25;ob.data.materials.append(text_mat);return ob
def rock(name,ore,p,scale=1,rot=(.45,.25,-.35)):
    source=assets[name+'_LOD0'];ob=bpy.data.objects.new('Preview_'+name,source.data.copy());preview.objects.link(ob)
    ob.location=p;ob.scale=(scale,)*3;ob.rotation_euler=rot
    ob.data.materials[1]=bpy.data.materials['Barren_Regolith' if ore=='barren' else 'Ore_'+ore]
    return ob
def clear():
    for ob in list(preview.objects):bpy.data.objects.remove(ob,do_unlink=True)
def render(name,width,height,span):
    scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.resolution_percentage=100
    camera.data.ortho_scale=span
    scene.render.filepath=str(OUT/'previews'/f'{name}.tmp.png')
    bpy.ops.render.render(write_still=True)
    (OUT/'previews'/f'{name}.tmp.png').replace(OUT/'previews'/f'{name}.png')
    print('RENDERED',name,flush=True)

# Main image: large samples under the same lighting, backed by smaller natural rocks.
text('B E L T   R U N N E R   3 D',(0,6.4,0),.48)
text('TEXTURED ASTEROIDS  /  BLENDER ASSET PREVIEW',(0,5.65,0),.20)
rock('lumpy_A','iron',(-8.6,1.6,0),1.8,(.6,.4,-.45))
rock('jagged_B','copper',(-4.3,-.5,0),1.85,(.8,.1,.4))
rock('chunk_A','gold',(.9,1.0,0),2.1,(.4,.7,.25))
rock('boulder_B','platinum',(7.3,1.0,0),2.0,(.75,.15,-.45))
rock('cluster_A','crystal',(5.1,-3.9,0),1.3,(.8,.4,-.25))
rock('hollow_B','barren',(1.0,4.2,-3),1.25,(.10,.22,.2))
rng=random.Random(791)
for i in range(42):
    x,y=rng.uniform(-12,12),rng.uniform(-6,5)
    if any((x-a)**2+(y-b)**2<9 for a,b in [(-8.6,1.6),(-4.3,-.5),(.9,1),(7.3,1),(5.1,-3.9)]):continue
    rock(rng.choice(['lumpy_B','chunk_B','shard_A','boulder_A','potato_B']), 'barren', (x,y,-5),rng.uniform(.08,.30),tuple(rng.uniform(0,6) for _ in range(3)))
text('BROAD METAL SEAMS   /   NATURAL SHAPES   /   REFLECTED SUNLIGHT',(-2,-6.0,0),.20)
quick='--quick' in sys.argv
render('hero',1200 if quick else 1920,750 if quick else 1200,25)
if quick:sys.exit(0)
clear()

families=['lumpy','chunk','potato','shard','pancake','cratered','cluster','slab','spindle','bean','boulder','jagged','wedge','hollow']
core=['iron','copper','gold','platinum','crystal']
text('14 SHAPE FAMILIES  /  TWO VARIATIONS EACH',(0,8.3,0),.42)
text('ACTUAL BLENDER MODELS  -  SHARED PBR TEXTURES  -  THREE DETAIL LEVELS',(0,7.65,0),.18)
for i,shape in enumerate(families):
    for j,var in enumerate('AB'):
        col=i%7;row=(i//7)*2+j;x=(col-3)*4.1;y=5.5-row*3.45
        obj=rock(shape+'_'+var,core[i%5],(x,y,0),1,(.35,.35,.45 if j else -.3))
        longest=max(obj.dimensions)
        obj.scale=(2.55/longest,)*3
        if shape=='hollow':obj.rotation_euler=(.10,.22,.2)
        text(shape.upper()+'  /  '+var,(x,y-1.5,0),.20)
text('HOLLOW A: DEEP POCKET     |     HOLLOW B: THROUGH-ARCH',(0,-7.35,0),.19)
render('shape-library',1960,1176,29)
clear()

ores=['iron','copper','gold','platinum','crystal','barren','cobalt','beryl','sulfur','emberite','he3','glacite','nebulite','voidpearl','iridium','rhodium','obsidian','darkmatter']
labels=['IRON','COPPER','GOLD','PLATINUM','VOIDCRYSTAL','BARREN','COBALT','BERYL','SULFUR GLASS','EMBERITE','HELIUM-3 ICE','GLACITE','NEBULITE','VOID PEARL','IRIDIUM','RHODIUM','OBSIDIAN ORE','DARK-MATTER SHARD']
text('ORE MATERIAL LIBRARY',(0,7.35,0),.48)
text('17 ORE TYPES + BARREN  /  METALLIC REFLECTIONS  /  NO EMISSION',(0,6.65,0),.20)
for i,(ore,label) in enumerate(zip(ores,labels)):
    x=(i%6-2.5)*4.15;y=4.8-(i//6)*4.25
    rock('lumpy_A',ore,(x,y,0),1.2,(.6,.4,-.45))
    text(label,(x,y-1.8,0),.21)
text('COLOR IS THE GAME PALETTE; LIGHT RESPONSE IS PHYSICALLY BASED',(0,-6.1,0),.18)
render('ore-library',1920,1152,26)
# Store a clean ready-to-render example alongside the editable asset library.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'asteroid_studio.blend'))
