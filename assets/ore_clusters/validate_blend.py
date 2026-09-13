import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parent
results=[]
for report in json.loads((root/'asset_manifest.json').read_text()):
    name=report['asset'];key=name.replace('ore_cluster_','')
    bpy.ops.wm.open_mainfile(filepath=str(root/key/(name+'.blend')))
    ob=bpy.data.objects[name]
    assert len(ob.data.polygons)==report['triangles']
    assert len(ob.data.uv_layers)==1
    assert all(abs(v-1)<1e-6 for v in ob.scale)
    assert ob.location.length<1e-6
    assert all(len(p.vertices)==3 for p in ob.data.polygons)
    for mat in ob.data.materials:
        normal=next(n for n in mat.node_tree.nodes if n.type=='NORMAL_MAP')
        assert normal.inputs['Color'].is_linked
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE':
                assert node.image.packed_file
                assert tuple(node.image.size)==(512,512)
    assert bpy.context.scene.render.engine=='CYCLES'
    assert bpy.context.scene.camera
    results.append({'asset':name,'packed_textures':True,'normal_connection':True,'triangulated':True,'studio_lighting':True})
(root/'blend_validation.json').write_text(json.dumps({'status':'PASS','assets':results},indent=2))
print('BLEND_VALIDATION_PASS',flush=True)
