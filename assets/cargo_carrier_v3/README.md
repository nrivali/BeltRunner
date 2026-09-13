# Rounded Cargo Carrier

The approved civilian freighter concept, built as an editable Blender asset and integrated into Belt Runner. The hull has broad curved shoulders, a tapered bow, ivory alloy plating over a graphite keel, restrained ochre markings, and three engines arranged in a triangular stern cluster. The central through-hangar remains open and usable from either side.

## Files

- `cargo_carrier.blend`: editable model, packed texture maps, articulated mining dish, and Cycles studio cameras/lights.
- `cargo_carrier_assembled.glb`: complete runtime model, including the dish and gameplay attachment markers.
- `cargo_carrier_assembled.data.js`: byte-identical base64 copy for direct-file play and hosts without binary asset support.
- `cargo_carrier.glb` / `mining_dish.glb`: separate component exports for editing or reuse; the game loads only the assembled model.
- `preview.html`: interactive front, stern, and through-hangar views with the game's lighting and Meridian backdrop.
- `previews/preview_*.png`: Blender Cycles renders. `browser-*.png` and `in-game*.png` are browser captures.
- `source/approved-concept.png`: approved ImageGen design. `source/imagegen_*.png`: ImageGen material sources. Exact prompts and generation mode are recorded in `source/imagegen-prompts.json`.
- `textures/`: baked base color, tangent-space normal, packed metallic/roughness, and emissive maps. All maps are also embedded in the GLB.

## Materials and rendering

The hull and technical-panel source textures were generated with **built-in ImageGen**, then mapped and baked in Blender. The base-color atlas is 4096 × 4096; normal, metallic/roughness, and emissive atlases are 2048 × 2048. The ImageGen source scans are 1254 × 1254: the 4K atlas allocates UV space for the assembled ship and is not a claim that the source scans contain 4K detail. Surface variation, seams, panels, and bevels also come from authored geometry and Blender materials.

The Blender scene uses Cycles, AgX, a solar key, soft fill, and warm hangar and cool engine lighting. Runtime materials use the existing game sunlight, reflection environment, shadows, and tone mapping. Only the model and material textures are exported; the studio lighting is not added to the game. Existing two hangar lights and three engine effects are retained.

The assembled model has **31,056 triangles**, about 17% fewer than the previous carrier's 37,496. It uses four carrier mesh draws and three dish material draws before effects. The GLB is about 18.5 MB; direct-file base64 is larger on disk. This is one detailed hero asset, with a 4K albedo map as the main texture-memory tradeoff. See `asset_report.json` for exact geometry counts and map dimensions.

## Gameplay integration

`load-carrier.js` validates all 13 attachment markers, materials, mesh layout, and the articulated dish before installing the model. The original procedural carrier remains available if the model is missing or invalid. The new loader replaces the previous loader in the game. Docking pads, through-hangar clearance, cargo drop point, drones, mining aim/focus, and warp attachment behavior retain the existing interfaces.

Game coordinates are +X forward and +Y up. Engine anchors are `[-3480,220,0]`, `[-3480,-140,-470]`, and `[-3480,-140,470]`; runtime exhaust glows sit 100 units aft. The main hull keeps the existing 1800-unit beam and 1080-unit height. Hangar width is 840, with the existing raised-floor docking height preserved.

`hull-contact.js` uses the same exported longitudinal sections as the curved pressure hull, with conservative sphere inflation and closed engine envelopes. It replaces the previous rectangular player-collision outline outside the hangar. Existing bay-wall handling remains active inside the passage. Small decorative fittings are not separate collision meshes; asteroid displacement and mining self-occlusion retain their existing conservative bounds.

The integration is reconciled over Claude's committed flight-control updates. `change-proof.json` records the source commits, version changes, guarded edits, and backups; `package-validation.json` identifies the verified game version. No lighting, map, planet, colony, audio, or flight-control settings are changed by this asset update.

## Rebuild and validate

From the repository root, with Blender 5.2 installed:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python assets/cargo_carrier_v3/build_carrier.py
node assets/cargo_carrier_v3/package_asset.cjs
node tests/carrier-v3-hull-contact.cjs
node tests/cargo-carrier-v3-integration.cjs
node tests/cargo-carrier-v3-preview.cjs
```

The Blender script is standalone and includes the complete construction and baking pipeline. `assemble_builder.cjs`, `hull_geometry.py`, and `prepare_loader.cjs` preserve the derivation from the previous carrier; rebuilding with `build_carrier.py` does not require regenerating it. Integration/version scripts are guarded migration records, not part of ordinary asset rebuilding.

The preview test expects the workspace HTTP server at `http://127.0.0.1:49280/`; the game integration test creates its own local server. Browser tests use locally installed Chrome and Playwright. Validation records include model and game hashes so results can be matched to the tested files.

Validation covers both docking/departure directions, 18 clear passage rays, three dish aiming directions, focus and rim effects, arrival at the Hub, HTTP and direct-file model loading, script fallback, and missing/invalid asset handling. The collision suite checks 822 contacts around the curved sections and engine overlaps. The preview checks front/stern/hangar views, pause/resume, orbit, zoom, resize, and browser errors.
