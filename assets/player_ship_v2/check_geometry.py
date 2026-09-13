import bpy,math,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
source=(P/'build_player_ship.py').read_text(encoding='utf8')
exec(compile(source.split('# All variants get their own')[0],str(P/'build_player_ship.py'),'exec'))
yaw=empty('mining_dish_yaw',MOUNT);pitch=empty('mining_dish_pitch',(0,-3.8,8.6));bpy.context.view_layer.update()
def keep(o,parent):
    m=o.matrix_world.copy();o.parent=parent;o.matrix_world=m
keep(pitch,yaw);keep(objects['dish_yoke'],yaw);keep(objects['mining_dish'],pitch);bpy.context.view_layer.update()
diagnostic=(P/'inspect_clearance.py').read_text(encoding='utf8')
exec(compile(diagnostic[diagnostic.index('def tree(obs):'):],str(P/'inspect_clearance.py'),'exec'))
