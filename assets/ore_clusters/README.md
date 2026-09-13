# Belt Runner 3D — ore crystal clusters

Six faceted ore props built in Blender 5.2, using ImageGen crystal and asteroid texture sources. Each folder includes a self-contained GLB, editable Blender scene, four 512 × 512 PNG maps, and front/rear Cycles renders. The collection render shows their relative sizes under area lights with soft shadows and indirect illumination.

| Folder | GLB object / mesh name | Empties | Triangles | Height |
| --- | --- | --- | ---: | ---: |
| 01_needle | ore_cluster_01_needle | none | 444 | 20 |
| 02_fan | ore_cluster_02_fan | none | 584 | 30 |
| 03_crown | ore_cluster_03_crown | none | 514 | 40 |
| 04_split_spire | ore_cluster_04_split_spire | none | 444 | 60 |
| 05_ridge | ore_cluster_05_ridge | none | 444 | 25 |
| 06_bloom | ore_cluster_06_bloom | none | 584 | 45 |

GLBs use +Y up and +Z forward, with one game unit per Blender metre. The origin is at the centre of the mounting footprint, on its underside. Align local +Y to the asteroid surface normal and rotate about that normal to vary placement. All transforms are applied; GLBs contain no cameras or lights. Studio lighting and cameras are included in the Blender files.

Each GLB has one mesh with three material groups: `crystal_body`, `crystal_emissive`, and `asteroid_matrix`. Blender may append numeric suffixes to material names in the collection scene. The neutral crystal atlas supports recoloring both crystal materials; set the emissive material's color and emission color together. The rocky base remains independent. Default emission strength is 1.8. Glow halos require the game's bloom effect.

The four embedded maps are also supplied separately in each `textures` folder:

- `basecolor.png`: sRGB neutral mineral and charcoal rock color.
- `metallic_roughness.png`: linear data; roughness in green, metalness in blue (0.2).
- `normal.png`: linear tangent-space surface detail baked in Blender.
- `emissive.png`: sRGB mask/detail for selected crystal edges and tips.

Each mesh has one nonoverlapping UV set. Mineral materials use modest transmission (0.18), IOR 1.48, and glossy roughness (0.24); rock roughness is 0.86. Use an environment or suitable scene lighting for reflections. The generated sources and exact ImageGen prompts are in `source/`.

Run `build_ore_clusters.py` with Blender in background mode to regenerate all files. `tests/ore-cluster-assets.cjs` at the project root verifies the GLB structure, triangle budgets, dimensions, UV overlap, embedded textures, and loading/rendering in the game's Three.js r158. Results are in `validation.json`.

## Game integration

`belt-runner-3d.html` loads `load-ore-clusters.js`. Ore-bearing, non-cave asteroids retain their existing 60% detail chance. Each decorated rock receives one of the six shapes and its ore's color, aligned to actual surface triangles. Small rocks use one cluster, large rocks two, giants three, and colossals four. Props retain their authored size unless a small asteroid requires scaling down.

High detail activates within 3,500 units of the rock's base radius and releases beyond 4,500. A maximum of 96 rocks use detailed clusters, with two built per frame; each uses three instanced draw calls. Geometry, textures, and tinted materials are shared. Placements persist across detail changes. Distant rocks and failed asset loads use the original procedural crystals. Breaking rocks and zone changes release instance buffers. Mineral transmission is disabled in gameplay to avoid its extra render pass; normal maps, reflections, and separate emission remain active.

Run `node assets/ore_clusters/build-game-assets.cjs` after rebuilding GLBs to refresh the direct-HTML payload. HTTP play loads the six GLBs; `file://` play loads the generated `ore_clusters.data.js`. `tests/ore-integration.cjs` checks both modes, missing assets, color and surface orientation, detail limits, and mining cleanup.
