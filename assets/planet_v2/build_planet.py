"""Build the textured Ferron planet in Blender. Run blender -b -t 8 -P this_file.

ImageGen supplies the albedo. Blender bakes wrap/pole-safe albedo, a tangent
normal map and roughness, and creates shallow terrain inside the game collider.
"""
import bpy, math, json, random
from pathlib import Path
from mathutils import Vector, noise
import numpy as np

OUT = Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 1
scene.cycles.use_denoising = True
scene.render.bake.margin = 12
scene.view_settings.view_transform = 'AgX'
source = bpy.data.images.load(str(OUT/'source/imagegen_surface_detail.png'))
source.pack()
sw, sh = source.size
pixels = np.array(source.pixels[:], dtype=np.float32).reshape(sh, sw, 4)

def sample(u, v):
    # Match the node-based wrap/pole treatment when displacing the geometry.
    def at(x):
        return pixels[min(sh-1, int(v*(sh-1))), min(sw-1, int(x*(sw-1))), :3].mean()
    edge = max(0, 1-min(u, 1-u)/.045)
    edge = edge*edge*(3-2*edge)*.5
    lum = at(u)*(1-edge)+at(1-u)*edge
    pole = max(0, 1-min(v, 1-v)/.028)
    return lum*(1-pole)+.24*pole

bpy.ops.mesh.primitive_uv_sphere_add(segments=384, ring_count=192, radius=1)
planet = bpy.context.object
planet.name = 'Ferron_Terrain'
# Use the actual Blender UV layout so surface relief tracks the baked map.
uv = planet.data.uv_layers.active.data
vertex_uv = {}
for loop in planet.data.loops:
    vertex_uv.setdefault(loop.vertex_index, tuple(uv[loop.index].uv))
radii = []
for vert in planet.data.vertices:
    u, v = vertex_uv[vert.index]
    direction = vert.co.normalized()
    h = (sample(u, v)-.28)*.005
    h += noise.noise_vector(direction*32)[0]*.00016
    radius = max(.9980, min(1.0025, 1+h))
    vert.co = direction*radius
    radii.append(radius)
for face in planet.data.polygons:
    face.use_smooth = True

mat = bpy.data.materials.new('Ferron_Regolith_PBR')
mat.use_nodes = True
planet.data.materials.append(mat)
nt = mat.node_tree
nt.nodes.clear()
def node(kind, name=None):
    n = nt.nodes.new(kind)
    if name: n.label = name
    return n
def link(a, b): nt.links.new(a, b)
def mathnode(op, a, b=None):
    n = node('ShaderNodeMath'); n.operation = op
    if hasattr(a, 'node'): link(a, n.inputs[0])
    else: n.inputs[0].default_value = a
    if b is not None:
        if hasattr(b, 'node'): link(b, n.inputs[1])
        else: n.inputs[1].default_value = b
    return n.outputs[0]
uvn = node('ShaderNodeTexCoord')
sep = node('ShaderNodeSeparateXYZ'); link(uvn.outputs['UV'], sep.inputs[0])
u, v = sep.outputs['X'], sep.outputs['Y']
mirror = node('ShaderNodeCombineXYZ')
link(mathnode('SUBTRACT', 1, u), mirror.inputs['X']); link(v, mirror.inputs['Y'])
tex = node('ShaderNodeTexImage', 'ImageGen albedo source'); tex.image = source
tex2 = node('ShaderNodeTexImage'); tex2.image = source
link(uvn.outputs['UV'], tex.inputs[0]); link(mirror.outputs[0], tex2.inputs[0])
dist = mathnode('MINIMUM', u, mathnode('SUBTRACT', 1, u))
fac = node('ShaderNodeMapRange'); fac.clamp = True; fac.interpolation_type = 'SMOOTHSTEP'
link(dist, fac.inputs['Value']); fac.inputs['From Max'].default_value = .045
fac.inputs['To Min'].default_value = .5; fac.inputs['To Max'].default_value = 0
wrap = node('ShaderNodeMixRGB'); link(fac.outputs[0], wrap.inputs[0]); link(tex.outputs['Color'], wrap.inputs[1]); link(tex2.outputs['Color'], wrap.inputs[2])
polar = node('ShaderNodeMapRange'); polar.clamp = True; polar.interpolation_type = 'SMOOTHSTEP'
link(mathnode('MINIMUM', v, mathnode('SUBTRACT', 1, v)), polar.inputs['Value'])
polar.inputs['From Max'].default_value = .028
polar.inputs['To Min'].default_value = 1; polar.inputs['To Max'].default_value = 0
color = node('ShaderNodeMixRGB'); link(polar.outputs[0], color.inputs[0]); link(wrap.outputs[0], color.inputs[1]); color.inputs[2].default_value = (.24, .205, .17, 1)
gray = node('ShaderNodeRGBToBW'); link(color.outputs[0], gray.inputs[0])
bump = node('ShaderNodeBump'); bump.inputs['Strength'].default_value = .35; bump.inputs['Distance'].default_value = .0007
link(gray.outputs[0], bump.inputs['Height'])
# Fine-scale geology is generated at bake resolution, adding real detail beyond
# the global image. Sampling 3D object coordinates keeps it continuous at seams.
grain = node('ShaderNodeTexNoise', 'Fine regolith'); grain.inputs['Scale'].default_value = 640
grain.inputs['Detail'].default_value = 3; grain.inputs['Roughness'].default_value = .7
link(uvn.outputs['Object'],grain.inputs['Vector'])
craters = node('ShaderNodeTexVoronoi', 'Secondary impact field'); craters.inputs['Scale'].default_value = 82
link(uvn.outputs['Object'],craters.inputs['Vector'])
distance = craters.outputs['Distance']
pit = mathnode('EXPONENT', mathnode('MULTIPLY', mathnode('POWER', distance, 2), -100))
rim = mathnode('EXPONENT', mathnode('MULTIPLY', mathnode('POWER', mathnode('SUBTRACT',distance,.215), 2), -850))
micro_height = mathnode('ADD',mathnode('MULTIPLY',grain.outputs['Fac'],.28),mathnode('SUBTRACT',mathnode('MULTIPLY',rim,.42),mathnode('MULTIPLY',pit,.55)))
fine_bump = node('ShaderNodeBump', 'Regolith and small impact relief')
fine_bump.inputs['Strength'].default_value = .55; fine_bump.inputs['Distance'].default_value = .0004
link(micro_height,fine_bump.inputs['Height']); link(bump.outputs[0],fine_bump.inputs['Normal'])
color_factor = mathnode('ADD', .91, mathnode('ADD',mathnode('MULTIPLY',grain.outputs['Fac'],.16),mathnode('SUBTRACT',mathnode('MULTIPLY',rim,.10),mathnode('MULTIPLY',pit,.16))))
fine_color = node('ShaderNodeVectorMath'); fine_color.operation='SCALE'
link(color.outputs[0],fine_color.inputs[0]); link(color_factor,fine_color.inputs[3])
rough = node('ShaderNodeMapRange'); link(gray.outputs[0], rough.inputs['Value'])
rough.inputs['To Min'].default_value = .95; rough.inputs['To Max'].default_value = .74
bs = node('ShaderNodeBsdfPrincipled')
link(fine_color.outputs[0], bs.inputs['Base Color']); link(fine_bump.outputs[0], bs.inputs['Normal']); link(rough.outputs[0], bs.inputs['Roughness'])
bs.inputs['Metallic'].default_value = 0
output = node('ShaderNodeOutputMaterial'); link(bs.outputs[0], output.inputs['Surface'])

def bake(name, kind, size=(4096,2048), socket=None, color_space='Non-Color'):
    im = bpy.data.images.new(name, width=size[0], height=size[1], alpha=False)
    im.colorspace_settings.name = color_space
    target = node('ShaderNodeTexImage'); target.image = im; nt.nodes.active = target
    emission = None
    if socket:
        emission = node('ShaderNodeEmission'); link(socket, emission.inputs['Color']); link(emission.outputs[0], output.inputs['Surface'])
    bpy.ops.object.bake(type=kind)
    if emission:
        nt.nodes.remove(emission); link(bs.outputs[0], output.inputs['Surface'])
    im.filepath_raw = str(OUT/'textures'/name)
    im.file_format = 'JPEG' if name.endswith('.jpg') else 'PNG'
    im.save(quality=96); im.pack()
    nt.nodes.remove(target)
    return im

albedo = bake('surface_albedo.jpg', 'EMIT', socket=fine_color.outputs[0], color_space='sRGB')
normal = bake('surface_normal.png', 'NORMAL')
roughness = bake('surface_roughness.png', 'EMIT', (2048,1024), rough.outputs[0])
nt.nodes.clear()
bs = node('ShaderNodeBsdfPrincipled'); output = node('ShaderNodeOutputMaterial'); link(bs.outputs[0], output.inputs['Surface'])
base = node('ShaderNodeTexImage'); base.image = albedo; link(base.outputs[0], bs.inputs['Base Color'])
n = node('ShaderNodeTexImage'); n.image = normal
nmap = node('ShaderNodeNormalMap'); link(n.outputs[0], nmap.inputs[1]); link(nmap.outputs[0], bs.inputs['Normal'])
r = node('ShaderNodeTexImage'); r.image = roughness; link(r.outputs[0], bs.inputs['Roughness'])
bs.inputs['Metallic'].default_value = 0
planet['collision_radius'] = 1.006
planet['terrain_radius_max'] = max(radii)
planet['image_source'] = 'Built-in ImageGen; prompt preserved in source/imagegen-prompt.json'
bpy.ops.export_scene.gltf(filepath=str(OUT/'planet.glb'), export_format='GLB', use_selection=True,
    export_image_format='AUTO', export_texcoords=True, export_normals=True, export_tangents=True,
    export_extras=True, export_yup=True, export_cameras=False, export_lights=False)

# A real-light render of the exported asset's source mesh; no painted terminator.
world = bpy.data.worlds.new('Space')
world.use_nodes = True; world.node_tree.nodes['Background'].inputs[0].default_value = (.005,.008,.015,1)
world.node_tree.nodes['Background'].inputs[1].default_value = .08; scene.world = world
sun_data = bpy.data.lights.new('Solar_key', 'SUN'); sun_data.energy = 3.2; sun_data.angle = .009
sun = bpy.data.objects.new('Solar_key', sun_data); scene.collection.objects.link(sun)
sun.rotation_euler = Vector((.8,.7,-.4)).to_track_quat('-Z','Y').to_euler()
cam_data = bpy.data.cameras.new('Orbit_preview'); cam = bpy.data.objects.new('Orbit_preview',cam_data); scene.collection.objects.link(cam)
cam.location = (0,-4.2,1.05); cam.rotation_euler = (-cam.location).to_track_quat('-Z','Y').to_euler(); cam_data.lens = 50
scene.camera = cam
scene.render.resolution_x = 1440; scene.render.resolution_y = 1080; scene.render.resolution_percentage = 100
scene.cycles.samples = 48
scene.render.resolution_x = 1920; scene.render.resolution_y = 1440
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(OUT/'previews/blender-ferron.png')
scene.render.film_transparent = False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'planet.blend'))
bpy.ops.render.render(write_still=True)
report = dict(source_size=[sw,sh],vertices=len(planet.data.vertices),triangles=sum(len(p.vertices)-2 for p in planet.data.polygons),
    radius_min=float(min(radii)),radius_max=float(max(radii)),collision_radius=1.006,textures={im.name:list(im.size) for im in [albedo,normal,roughness]},
    fine_detail='3D regolith noise and secondary impact rims baked natively into the 4096x2048 color and normal maps',
    lighting='Blender Cycles, directional sun with 0.009 rad angular diameter, AgX, dark environment; no emissive surface')
(OUT/'asset-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
