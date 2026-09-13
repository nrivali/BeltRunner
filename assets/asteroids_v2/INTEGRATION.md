# Asteroid integration — game 0.9.19

The game now renders the approved Blender rocks throughout its belts and barren scenery. Existing ore types, shape weights, size classes, quantities, health, respawns and zone distributions are retained. New rocks and mining fragments select one of the two mesh variations for their shape family. There are no separate attached ore nodes.

`build-game-assets.cjs` reads the three final GLB libraries and produces `asteroids-game.bin.gz` plus `asteroids-game.data.js`. Positions and UVs retain their float precision; normals and tangents use normalized 16-bit attributes. A per-vertex ore mask merges stone and ore into one primitive. The compressed runtime library is 21,740,967 bytes and contains all 84 meshes and the six shared ImageGen/Blender PBR texture maps. Rebuild it with:

```powershell
node assets/asteroids_v2/build-game-assets.cjs
```

`load-asteroids.js` loads the compressed binary over HTTP. Direct-file play and hosts that refuse that file use the equivalent base64 script copy. Browsers that already expand an HTTP Content-Encoding response are also supported. Invalid or missing data retains the existing procedural rocks and their older texture loader. Gameplay remains available while the new library loads.

Visible rocks are grouped by shape, variation and detail level into `InstancedMesh` batches. Every batch shares the same PBR shader, with per-instance ore color, roughness, metalness and damage heat. Frustum culling and projected screen size select LODs with hysteresis. Subpixel rocks retain the existing belt-point representation. Intact ore has no emission; its shine comes from the game's sun and environment map. Laser spot heat and whole-rock damage heat remain independent for every rock.

`mesh-collision.js` builds shared triangle BVHs from the original high-detail geometry when required. Ship collisions query the closest surface and distinguish solid stone from cavity space. Raycasts aim both ship and cargo-ship lasers at visible surfaces. Manual rays can pass through arch openings, while automatic aim selects an actual wall. Scorch marks use the mesh surface normal. Asteroid collision bounds include long shards and spindles, and the ship's swept path is sampled in shorter steps to avoid skipping thin rocks. Shared geometry is retained when individual rocks break or zones change.

The game still simulates its existing rock orbit, collision broad phase, fragments and ore drops. Destroyed rocks leave the batches on the next render. Mineable fragments use the appropriate shape family; scrap uses the new stone geometry and texture with the existing cooling behavior. Zone changes reuse the geometry and textures instead of allocating a unique body mesh for each new rock.

Validation commands:

```powershell
node tests/asteroids-v2-integration.cjs
node tests/rock-surface-integration.cjs
node tests/carrier-integration.cjs
node tests/player-integration.cjs
```

The integration suite checks HTTP and direct-file loading, script fallback, missing and corrupt data, all live asteroid/scenery attachments, shader compilation, ship clearance through an arch, surface collision, manual/automatic mining aim, heat, scorch marks, breakable fragments, textured scrap, LOD selection, zone transitions, departure and sustained mining. The original rock-texture suite explicitly exercises the retained fallback. The player missing-assets regression blocks both GLB and script delivery paths.

In the deterministic 1,000-rock test field, 944 visible rocks rendered in **26 draw calls** with 1,363,522 triangles. From farther away all 1,000 used LOD 2, with 621,298 triangles and 14 draw calls. This verifies batching and LOD use; it is not an FPS guarantee for every device. Detailed results, including the live simulation measurement, are in `integration-validation.json`. `previews/integrated-field.png` shows the arranged stress field; `previews/in-game.png` shows a rock under the actual game's lighting.

The integration started from Claude's commit `20923ec`. `integration-change.json` records the immediate pre-edit backup and file hashes. Audio, ship assets and GitHub Pages configuration were preserved.
