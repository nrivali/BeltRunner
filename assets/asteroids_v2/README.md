# Textured asteroid asset library

Blender assets based on the approved **Recognition at Distance** concept. The set preserves all 14 current game shape families, with two variations per family, three detail levels, and all 17 ore materials plus barren rock. This is an asset delivery; the live game's asteroid generation, mining, collisions and rendering have not been replaced.

- `asteroids.blend`: editable library with all 84 meshes, all 18 materials, and packed PBR textures. LOD 0 is visible in the viewport; lower detail meshes are hidden. Assets retain the current shape names and nominal base radius 1.
- `asteroid_studio.blend`: ready-to-render material lineup with Cycles sunlight and broad reflected fill.
- `asteroids_lod0.glb`, `asteroids_lod1.glb`, `asteroids_lod2.glb`: 28 models per file, with embedded textures and standard `KHR_materials_variants` entries for every ore and barren rock.
- `textures/`: six 1024 × 1024 maps: regolith and neutral ore albedo, tangent-space normal, and packed metallic/roughness. Roughness is in G, metalness in B. Albedo uses sRGB; data maps use linear/non-color.
- `source/`: the approved image, the two original ImageGen texture sources, and the exact prompts in `imagegen-prompts.json`. The built-in ImageGen tool produced the sources; Blender baked the portable PBR maps.
- `previews/`: actual Blender renders of the shape library, ore lineup, and hero arrangement, plus an actual Three.js GLB screenshot.
- `preview.html`: interactive GLB viewer with shape, variation, ore and LOD controls. Drag to orbit, scroll to inspect distance, and rotate the rock to watch the metallic reflections.
- `asset-report.json`, `manifest.json`, `validation.json`: geometry, material and validation records.

The shape families are lumpy, chunk, potato, shard, pancake, cratered, cluster, slab, spindle, bean, boulder, jagged, wedge and hollow. Hollow A has a deep pocket; hollow B has a through-arch. Cluster shapes are continuous fused stone bodies. Ore regions are cut into the surface topology and assigned a reflective material, so there are no attached ore nodes, hovering surfaces, or added ore protrusions.

Ore covers approximately 31–36% of the high-detail surface. Dark, rough stone contrasts with silver iron, orange copper, yellow gold, teal platinum, violet voidcrystal and the remaining regional game colors. Brighter native-metal color factors improve reflectance while retaining the game's color families. No ore emits light. Metal highlights move with the lighting and view; shadows and highlights are not baked into albedo. The mineral colors are the game's visual language rather than mineralogical claims.

Near models contain 4,778–10,358 triangles; medium models 1,322–2,902; distant models 310–752. Each ore-bearing rock has two material primitives. All models share six texture images within each GLB. The GLB sizes are approximately 27.7 MB, 16.9 MB and 12.9 MB. These are interchange assets; full-belt loading, instancing, texture compression, draw-call budgets and LOD transitions still need to be measured during game integration.

To preview locally from the project root:

```powershell
node assets/asteroids_v2/serve-preview.cjs
```

Open the loopback URL printed by the server. Direct `file://` opening cannot fetch the GLBs. The viewer uses the project's existing Three.js r158 files and needs no internet or packages.

To rebuild from the project root:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b -t 12 --python assets/asteroids_v2/build_asteroids.py
node assets/asteroids_v2/package_assets.cjs
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b -t 12 --python assets/asteroids_v2/render_previews.py
node tests/asteroids-v2-assets.cjs
```

The packaging step preserves the Blender material tint factors that this exporter omits from its MixRGB node conversion, removes export-only material templates, and adds the material variants. Use the final `.glb` files, not the ignored `.raw.glb` intermediates.

For integration, select `<shape>_<A|B>_LOD<0|1|2>` from the desired GLB and reset its gallery translation to zero. glTF uses the game's Y-up coordinates; dimensions recorded by Blender in `asset-report.json` use Blender Z-up. Apply the asteroid's base radius and orientation, then compute bounds from the resulting geometry. The standard material variant extension maps the ore primitive to each named material and to the stone material for barren rocks. Loaders without variant support show iron by default; `preview.html` demonstrates explicit material selection using the existing loader.

The current game uses procedural collision profiles. Those must be reconciled with these new silhouettes during integration, especially for the hollow pocket, through-arch, clustered bodies, mining raycasts and spawned fragments. The asset validation checks that the deep pocket is retained and the arch center is clear at every LOD, but does not claim live gameplay collision or full-belt performance validation.

Validation passed for all 84 closed meshes, all three GLB libraries, all texture maps and material variants, finite vertex attributes, declining LOD triangle counts, real Three.js loading/rendering, and cave/arch raycasts. No WebGL shader errors were reported. The game file receives only its required asset-commit version bump, to 0.9.18.
