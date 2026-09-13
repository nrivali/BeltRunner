import bpy,math,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'player_ship.blend'))
def tree(obs):
    v=[];f=[]
    for o in obs:
        k=len(v);v.extend(o.matrix_world@p.co for p in o.data.vertices);f.extend(tuple(k+i for i in p.vertices) for p in o.data.polygons)
    return BVHTree.FromPolygons(v,f,all_triangles=True)
fixed={n:tree([bpy.data.objects[n]]) for n in ['hull','hull_trim','canopy','cockpit','cockpit_frame','engine_core','emissive','engine_nacelle_3','cargo_pod_3','scanner_dish_3']}
yaw=bpy.data.objects['mining_dish_yaw'];pitch=bpy.data.objects['mining_dish_pitch'];barrel=bpy.data.objects['laser_barrel_3'];world=barrel.matrix_world.copy();barrel.parent=pitch;barrel.matrix_world=world
hits={}
for angle in [-90,-60,-30,-10,0,10,30,60,90]:
    for elev in [-.7,-.35,0,.65,1.3]:
        yaw.rotation_euler.z=math.radians(angle);pitch.rotation_euler.x=elev;bpy.context.view_layer.update()
        for moving in ['dish_yoke','mining_dish','laser_barrel_3']:
            t=tree([bpy.data.objects[moving]])
            for name,st in fixed.items():
                overlap=st.overlap(t)
                if overlap:
                    key=name+' vs '+moving;hits.setdefault(key,[]).append([angle,elev,len(overlap)])
print('CLEARANCE_HITS',json.dumps(hits))
for azimuth,elevation in [(0,0),(0,-.7),(90,-.7)]:
    yaw.rotation_euler.z=math.radians(azimuth);pitch.rotation_euler.x=elevation;bpy.context.view_layer.update()
    pairs=fixed['hull_trim'].overlap(tree([bpy.data.objects['mining_dish']]))
    centers=[];o=bpy.data.objects['hull_trim']
    for index in sorted(set(i for i,j in pairs)):
        c=o.matrix_world@o.data.polygons[index].center;centers.append([round(c.x,3),round(c.z,3),round(-c.y,3)])
    print('STATIC_CONTACTS',azimuth,elevation,centers[:40])
