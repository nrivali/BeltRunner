# Meridian Garden Habitat

The selected Garden Habitat concept is built as an editable Blender asset and integrated into the local v0.9.57 game. The station retains the two concentric rings, fixed civic hub, terminal berths and landing-pad positions from Claude's v0.9.56. The Hub still contains one colony.

The model adds 40 glazed conservatories, 504 trees, planted promenades, ivory ceramic-alloy pressure hulls, warm residential windows, structural glass ribs, solar wings and an independently moving communications dish. Docking remains on the fixed central structure while the habitat rings turn together.

## Files

- `garden-habitat.blend` — editable Blender source with packed textures, Cycles sun lighting, reflected planetary fill and a render camera.
- `garden-habitat.glb` — game model with embedded PBR materials and textures.
- `garden-habitat.data.js` — equivalent script transport for direct-file loading or failed binary requests.
- `preview.html` — interactive model viewer with Meridian behind the station; orbit, zoom, inspect gardens and terminals, pause rotation.
- `build_colony.py` — deterministic Blender construction and texture-map baking.
- `load-colony.js` — cached asset loader, safe replacement, animation and resource lifetime.
- `source/approved-concept.png` — selected Garden Habitat concept.
- `source/imagegen-prompts.json` — complete prompts and built-in ImageGen provenance.
- `source/imagegen_*.png` — original ImageGen hull, planted-ground and foliage color textures.
- `textures/` — Blender-baked hull normal and roughness maps.
- `previews/` — Blender render and actual browser screenshots.
- `asset-report.json` — geometry and material-batch counts.
- `*-validation.json` — real browser test results, with game/asset/loader hashes.
- `change-proof.json` — immediate pre-edit backup and exact game-file patch provenance.

## Materials and lighting

Three color textures were generated using the built-in ImageGen tool. The hull normal and roughness maps were baked in Blender. Surface detail, metal response, transparent pressure glass and warm emission use glTF PBR materials; no sunlight or cast shadows are baked into the color maps. Glass opacity increases toward grazing angles in the runtime shader. The game uses its existing solar direction, exposure, reflection environment and local shadow system. The Blender scene also includes a soft blue reflected fill for asset inspection.

The geometry is authored at 1/1000 game scale and exported with glTF Y-up. The loader scales the asset by 1000. Pressure hull sizes and all 20 landing surfaces match the existing game. Garden roofs remain within the ring collision envelopes; the original decorative navigation pylons are not separately collidable.

## Runtime budget and lifecycle

The full colony is merged into 23 material batches across the ring, core and dish assemblies. It uses about 244,000 triangles before shadow passes. The game still draws its existing traffic and planets separately. Geometry and texture resources are shared between visits; they are not recreated when returning to the Hub. The prior colony remains visible while the model loads, and remains usable if both the binary asset and script fallback are unavailable. A completed download cannot attach to a colony that has already been removed.

## Rebuild and verify

Run from the repository root:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python assets/colony_garden/build_colony.py
node assets/colony_garden/package_asset.cjs
node tests/garden-colony-integration.cjs http
node tests/garden-colony-integration.cjs file
node tests/garden-colony-integration.cjs script
node tests/garden-colony-integration.cjs missing
```

The browser checks load the actual GLB and textures, inspect the 20 landing surfaces, verify ring motion and collision response, revisit the Hub three times, check shared-resource retention and late-download removal, exercise fallback loading, and verify the interactive preview controls. They use local Chrome and the existing workspace Playwright dependency. No new runtime libraries or external asset downloads are required.

`integrate.cjs` records the original narrow v0.9.56-to-v0.9.57 integration. It is a guarded provenance script, not a tool for replacing newer game versions. Read `AGENTS.md` before any future change to the shared game or publication.
