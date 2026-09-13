"""Separate the ceiling liner from the pressure hull without rebaking its textures.

Run with Blender --background --python assets/cargo_carrier_v3/repair_hangar_ceiling.py.
The matching builder correction makes newly built carriers use this clearance too.
"""
import bpy
import base64
import hashlib
import json
import shutil
import struct
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
SHIFT = 6.0

def sha(data):
    return hashlib.sha256(data).hexdigest()

def ceiling_corner(x, y, z, repaired=False):
    low, high = (170, 184) if repaired else (176, 190)
    return (abs(abs(x)-420) < .01 and abs(abs(z)-900) < .01
            and (abs(y-low) < .01 or abs(y-high) < .01))

def repair_glb(data):
    magic, version, total = struct.unpack_from('<III', data)
    assert (magic, version, total) == (0x46546c67, 2, len(data))
    length, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4e4f534a
    gltf = json.loads(data[20:20+length])
    bin_length, bin_kind = struct.unpack_from('<II', data, 20+length)
    assert bin_kind == 0x004e4942 and 28+length+bin_length == len(data)
    binary = bytearray(data[28+length:])
    node = next(n for n in gltf['nodes'] if n['name'] == 'interior')
    assert not any(k in node for k in ('matrix', 'rotation', 'scale', 'translation'))
    primitive, = gltf['meshes'][node['mesh']]['primitives']
    acc = gltf['accessors'][primitive['attributes']['POSITION']]
    assert acc['componentType'] == 5126 and acc['type'] == 'VEC3'
    view = gltf['bufferViews'][acc['bufferView']]
    start = view.get('byteOffset', 0)+acc.get('byteOffset', 0)
    stride = view.get('byteStride', 12)
    rows = [struct.unpack_from('<fff', binary, start+i*stride) for i in range(acc['count'])]
    old = [i for i, p in enumerate(rows) if ceiling_corner(*p)]
    fixed = [i for i, p in enumerate(rows) if ceiling_corner(*p, repaired=True)]
    if not old:
        assert len(fixed) == 24, 'Unexpected ceiling layout'
        return data, 0
    assert len(old) == 24 and not fixed
    for i in old:
        x, y, z = rows[i]
        rows[i] = (x, y-SHIFT, z)
        struct.pack_into('<f', binary, start+i*stride+4, y-SHIFT)
    acc['min'] = [min(p[axis] for p in rows) for axis in range(3)]
    acc['max'] = [max(p[axis] for p in rows) for axis in range(3)]
    # Embedded PNGs, UVs, normals, indices, rig and attachment markers stay byte-identical.
    original_bin = data[28+length:]
    for image in gltf['images']:
        image_view = gltf['bufferViews'][image['bufferView']]
        lo = image_view.get('byteOffset', 0)
        hi = lo+image_view['byteLength']
        assert bytes(binary[lo:hi]) == original_bin[lo:hi]
    encoded = json.dumps(gltf, separators=(',', ':')).encode()
    encoded += b' '*((-len(encoded)) % 4)
    result = (struct.pack('<III', magic, version, 28+len(encoded)+len(binary))
              +struct.pack('<II', len(encoded), kind)+encoded
              +struct.pack('<II', len(binary), bin_kind)+binary)
    return result, len(old)

files = [OUT/name for name in ('cargo_carrier.blend', 'cargo_carrier.glb',
         'cargo_carrier_assembled.glb', 'cargo_carrier_assembled.data.js')]
before = {p: p.read_bytes() for p in files}
exports = {p: repair_glb(before[p]) for p in files if p.suffix == '.glb'}
bpy.ops.wm.open_mainfile(filepath=str(files[0]))
interior = bpy.data.objects['interior']
old_vertices = [v for v in interior.data.vertices if ceiling_corner(v.co.x, v.co.z, -v.co.y)]
fixed_vertices = [v for v in interior.data.vertices if ceiling_corner(v.co.x, v.co.z, -v.co.y, repaired=True)]
assert (len(old_vertices), len(fixed_vertices)) in ((8, 0), (0, 8))
assert all(count == (24 if old_vertices else 0) for _, count in exports.values())
if old_vertices:
    backup = ROOT/'backups'/('hangar-ceiling-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(parents=True)
    for p in files:
        assert p.read_bytes() == before[p], 'Asset changed during repair'
        shutil.copy2(p, backup/p.name)
    for v in old_vertices:
        v.co.z -= SHIFT
    interior.data.update()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(files[0]))
    for p, (data, _) in exports.items():
        assert p.read_bytes() == before[p]
        p.write_bytes(data)
    data = exports[OUT/'cargo_carrier_assembled.glb'][0]
    files[-1].write_text('window.BeltRunnerCarrierData="'+base64.b64encode(data).decode()+'";\n', encoding='utf8')
    report = {'passed': True, 'ceilingUndersideY': 170, 'hullCeilingY': 176,
              'clearance': SHIFT, 'blenderVerticesMoved': len(old_vertices),
              'exportVerticesMoved': {p.name: count for p, (_, count) in exports.items()},
              'embeddedTexturesUnchanged': True, 'backup': str(backup),
              'files': {p.name: {'beforeSHA256': sha(before[p]), 'afterSHA256': sha(p.read_bytes())} for p in files}}
    (OUT/'ceiling-repair.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print('CEILING_REPAIR '+json.dumps(report), flush=True)
else:
    print('CEILING_REPAIR already repaired; Blender and both exports agree', flush=True)
