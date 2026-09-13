"""Build Meridian in Blender: ImageGen surface/clouds, PBR oceans and night lights.
Run: blender -b -t 8 -P assets/hub_planet/build_homeworld.py
"""
import bpy, math, json, tempfile
from pathlib import Path
from mathutils import Vector

OUT=Path(__file__).resolve().parent
scratch=OUT.parents[1]/'backups'/'blender-hub-temp'; scratch.mkdir(parents=True,exist_ok=True); tempfile.tempdir=str(scratch)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=1
scene.render.bake.margin=12; scene.view_settings.view_transform='AgX'
source=bpy.data.images.load(str(OUT/'source/imagegen-homeworld.png')); source.pack()
cloud_source=bpy.data.images.load(str(OUT/'source/imagegen-clouds.png')); cloud_source.colorspace_settings.name='Non-Color'; cloud_source.pack()
bpy.ops.mesh.primitive_uv_sphere_add(segments=256, ring_count=128, radius=1)
surface=bpy.context.object; surface.name='Meridian_Surface'
for face in surface.data.polygons: face.use_smooth=True
mat=bpy.data.materials.new('Meridian_Oceans_Continents'); mat.use_nodes=True; surface.data.materials.append(mat)
nt=mat.node_tree; nt.nodes.clear()
def node(kind): return nt.nodes.new(kind)
def link(a,b): nt.links.new(a,b)
def mathnode(op,a,b=None):
    n=node('ShaderNodeMath'); n.operation=op
    if hasattr(a,'node'): link(a,n.inputs[0])
    else: n.inputs[0].default_value=a
    if b is not None:
        if hasattr(b,'node'): link(b,n.inputs[1])
        else: n.inputs[1].default_value=b
    return n.outputs[0]
def ramp(value,lo,hi,a=0,b=1):
    n=node('ShaderNodeMapRange'); n.clamp=True; n.interpolation_type='SMOOTHSTEP'
    link(value,n.inputs['Value']); n.inputs['From Min'].default_value=lo; n.inputs['From Max'].default_value=hi
    n.inputs['To Min'].default_value=a; n.inputs['To Max'].default_value=b
    return n.outputs[0]
uv=node('ShaderNodeTexCoord'); tex=node('ShaderNodeTexImage'); tex.image=source
link(uv.outputs['UV'],tex.inputs[0])
# Blend matching longitudes only within a narrow seam, and converge polar colors.
xyz=node('ShaderNodeSeparateXYZ'); link(uv.outputs['UV'],xyz.inputs[0]); u,v=xyz.outputs['X'],xyz.outputs['Y']
mirror=node('ShaderNodeCombineXYZ'); link(mathnode('SUBTRACT',1,u),mirror.inputs[0]); link(v,mirror.inputs[1])
opposite=node('ShaderNodeTexImage'); opposite.image=source; link(mirror.outputs[0],opposite.inputs[0])
seam=ramp(mathnode('MINIMUM',u,mathnode('SUBTRACT',1,u)),0,.018,.5,0)
color=node('ShaderNodeMixRGB'); link(seam,color.inputs[0]); link(tex.outputs[0],color.inputs[1]); link(opposite.outputs[0],color.inputs[2])
polar=ramp(mathnode('MINIMUM',v,mathnode('SUBTRACT',1,v)),0,.025,1,0)
polar_color=node('ShaderNodeMixRGB'); link(polar,polar_color.inputs[0]); link(color.outputs[0],polar_color.inputs[1]); polar_color.inputs[2].default_value=(.7,.78,.84,1)
rgb=node('ShaderNodeSeparateColor'); link(polar_color.outputs[0],rgb.inputs[0])
ratio=mathnode('DIVIDE',rgb.outputs['Blue'],mathnode('ADD',mathnode('MAXIMUM',rgb.outputs['Red'],rgb.outputs['Green']),.0001))
ocean=ramp(ratio,1.20,1.6); land=mathnode('SUBTRACT',1,ocean)
# Slight surface grain is baked at full resolution. Oceans retain smooth normals.
grain=node('ShaderNodeTexNoise'); grain.inputs['Scale'].default_value=750; grain.inputs['Detail'].default_value=3
link(uv.outputs['Object'],grain.inputs[0])
factor=mathnode('ADD',1,mathnode('MULTIPLY',land,mathnode('MULTIPLY',mathnode('SUBTRACT',grain.outputs['Fac'],.5),.13)))
fine=node('ShaderNodeVectorMath'); fine.operation='SCALE'; link(polar_color.outputs[0],fine.inputs[0]); link(factor,fine.inputs[3])
roughness=mathnode('ADD',.18,mathnode('MULTIPLY',land,.64))
bump=node('ShaderNodeBump'); bump.inputs['Strength'].default_value=.25; bump.inputs['Distance'].default_value=.00012
link(mathnode('MULTIPLY',grain.outputs['Fac'],land),bump.inputs['Height'])
bs=node('ShaderNodeBsdfPrincipled'); bs.inputs['Metallic'].default_value=0; bs.inputs['IOR'].default_value=1.333
link(fine.outputs[0],bs.inputs['Base Color']); link(roughness,bs.inputs['Roughness']); link(bump.outputs[0],bs.inputs['Normal'])
output=node('ShaderNodeOutputMaterial'); link(bs.outputs[0],output.inputs[0])
# Sparse, clustered city lights. Their runtime emission is gated by the sun.
city=node('ShaderNodeTexVoronoi'); city.inputs['Scale'].default_value=215; link(uv.outputs['Object'],city.inputs[0])
settlement=node('ShaderNodeTexNoise'); settlement.inputs['Scale'].default_value=11; settlement.inputs['Detail'].default_value=3; link(uv.outputs['Object'],settlement.inputs[0])
cities=mathnode('MULTIPLY',ramp(city.outputs['Distance'],.025,.13,1,0),ramp(settlement.outputs['Fac'],.54,.68))
cities=mathnode('MULTIPLY',cities,mathnode('MULTIPLY',land,mathnode('SUBTRACT',1,polar)))
night=node('ShaderNodeMixRGB'); night.inputs[1].default_value=(0,0,0,1); night.inputs[2].default_value=(1,.48,.105,1); link(cities,night.inputs[0])

def bake(name,kind,socket=None,size=(4096,2048),colorspace='Non-Color'):
    image=bpy.data.images.new(name,width=size[0],height=size[1],alpha=False); image.colorspace_settings.name=colorspace
    target=node('ShaderNodeTexImage'); target.image=image; nt.nodes.active=target
    emission=None
    if socket:
        emission=node('ShaderNodeEmission'); link(socket,emission.inputs[0]); link(emission.outputs[0],output.inputs[0])
    bpy.ops.object.bake(type=kind)
    if emission: nt.nodes.remove(emission); link(bs.outputs[0],output.inputs[0])
    image.filepath_raw=str(OUT/'textures'/name); image.file_format='JPEG' if name.endswith('.jpg') else 'PNG'; image.save(quality=95); image.pack(); nt.nodes.remove(target)
    return image
albedo=bake('homeworld_albedo.jpg','EMIT',fine.outputs[0],colorspace='sRGB')
normal=bake('homeworld_normal.png','NORMAL',size=(2048,1024))
rough=bake('homeworld_roughness.png','EMIT',roughness,size=(2048,1024))
emission=bake('homeworld_cities.png','EMIT',night.outputs[0],size=(2048,1024),colorspace='sRGB')
nt.nodes.clear(); bs=node('ShaderNodeBsdfPrincipled'); output=node('ShaderNodeOutputMaterial'); link(bs.outputs[0],output.inputs[0])
bs.inputs['Metallic'].default_value=0; bs.inputs['IOR'].default_value=1.333
for image,socket in [(albedo,'Base Color'),(rough,'Roughness'),(emission,'Emission Color')]:
    n=node('ShaderNodeTexImage'); n.image=image; link(n.outputs[0],bs.inputs[socket])
bs.inputs['Emission Strength'].default_value=.8
n=node('ShaderNodeTexImage'); n.image=normal; nm=node('ShaderNodeNormalMap'); link(n.outputs[0],nm.inputs['Color']); link(nm.outputs[0],bs.inputs['Normal'])

bpy.ops.mesh.primitive_uv_sphere_add(segments=192,ring_count=96,radius=1.008)
clouds=bpy.context.object; clouds.name='Meridian_Clouds'
for face in clouds.data.polygons: face.use_smooth=True
cloud_mat=bpy.data.materials.new('Meridian_Cloud_Layer'); cloud_mat.use_nodes=True
cloud_mat.surface_render_method='DITHERED'; clouds.data.materials.append(cloud_mat)
nt=cloud_mat.node_tree; nt.nodes.clear(); uv=node('ShaderNodeTexCoord'); tex=node('ShaderNodeTexImage'); tex.image=cloud_source; link(uv.outputs['UV'],tex.inputs[0])
xyz=node('ShaderNodeSeparateXYZ'); link(uv.outputs['UV'],xyz.inputs[0]); u,v=xyz.outputs['X'],xyz.outputs['Y']
mirror=node('ShaderNodeCombineXYZ'); link(mathnode('SUBTRACT',1,u),mirror.inputs[0]); link(v,mirror.inputs[1])
opposite=node('ShaderNodeTexImage'); opposite.image=cloud_source; link(mirror.outputs[0],opposite.inputs[0])
mix=node('ShaderNodeMixRGB'); link(ramp(mathnode('MINIMUM',u,mathnode('SUBTRACT',1,u)),0,.025,.5,0),mix.inputs[0]); link(tex.outputs[0],mix.inputs[1]); link(opposite.outputs[0],mix.inputs[2])
gray=node('ShaderNodeRGBToBW'); link(mix.outputs[0],gray.inputs[0])
bs=node('ShaderNodeBsdfPrincipled'); output=node('ShaderNodeOutputMaterial'); link(bs.outputs[0],output.inputs[0])
cloud_map=bake('homeworld_clouds.png','EMIT',gray.outputs[0],size=(4096,2048))
nt.nodes.clear(); bs=node('ShaderNodeBsdfPrincipled'); output=node('ShaderNodeOutputMaterial'); link(bs.outputs[0],output.inputs[0])
bs.inputs['Base Color'].default_value=(.94,.965,1,1); bs.inputs['Roughness'].default_value=1
n=node('ShaderNodeTexImage'); n.image=cloud_map; link(n.outputs['Color'],bs.inputs['Alpha'])

bpy.ops.object.select_all(action='DESELECT'); surface.select_set(True); clouds.select_set(True); bpy.context.view_layer.objects.active=surface
surface['source']='Built-in ImageGen base color; Blender-baked material maps'; surface['collision_radius']=1.006
clouds['layer']='Independent animated cloud shell; ImageGen opacity texture'
bpy.ops.export_scene.gltf(filepath=str(OUT/'homeworld.glb'),export_format='GLB',use_selection=True,export_image_format='AUTO',export_texcoords=True,export_normals=True,export_tangents=True,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)

world=bpy.data.worlds.new('Orbital darkness'); world.use_nodes=True; world.node_tree.nodes['Background'].inputs[0].default_value=(.008,.012,.022,1); world.node_tree.nodes['Background'].inputs[1].default_value=.07; scene.world=world
sd=bpy.data.lights.new('Warm solar key','SUN'); sd.energy=3.2; sd.angle=.009; sun=bpy.data.objects.new('Warm solar key',sd); scene.collection.objects.link(sun); sun.rotation_euler=Vector((.6,.3,-.45)).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Homeworld orbit'); camera=bpy.data.objects.new('Homeworld orbit',cd); scene.collection.objects.link(camera); camera.location=(0,-4.2,1.0); camera.rotation_euler=(-camera.location).to_track_quat('-Z','Y').to_euler(); cd.lens=52; scene.camera=camera
scene.render.resolution_x=1600; scene.render.resolution_y=1200; scene.render.resolution_percentage=100; scene.cycles.samples=32; scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(OUT/'previews/blender-homeworld.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'homeworld.blend')); bpy.ops.render.render(write_still=True)
report={'surface_source_size':list(source.size),'cloud_source_size':list(cloud_source.size),'surface_triangles':sum(len(p.vertices)-2 for p in surface.data.polygons),'cloud_triangles':sum(len(p.vertices)-2 for p in clouds.data.polygons),'textures':{im.name:list(im.size) for im in [albedo,normal,rough,emission,cloud_map]},'lighting':'Blender Cycles sun; unlit base-color textures, runtime night-side emission gate','collision_radius':1.006}
(OUT/'asset-report.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report))
