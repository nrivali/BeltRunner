# Belt Runner 3D — cargo carrier

Blender 5.2 model with Cycles studio renders. Export: Y up, forward +X, game-unit scale, four mesh/material groups, embedded 2048 PNG PBR atlas, one UV set, triangulated geometry. Lighting and camera are retained in the Blender scene only.

Meshes: `hull`, `interior`, `emissive`, `glass`. Empties: `hangar_mouth_pos`, `hangar_mouth_neg`, `pad_pos`, `pad_neg`, `drop_pad`, `dish_mount`, `engine_0`, `engine_1`, `engine_2`, `drone_dock_0`, `drone_dock_1`, `drone_dock_2`, `bridge_windows`. Triangle count and exact coordinates: `asset_report.json`.

The mining dish is the separate asset 4; this carrier includes its mast and attachment point. Window glass uses opaque luminous panes for predictable browser rendering. Surface details are geometry; the supplied normal atlas is neutral. Metallic/roughness texture uses glTF channels: G roughness, B metallic. Shared texture atlases have individual padded polygon islands.

Preview files: `preview_front.png`, `preview_rear.png`, `preview_hangar.png`. These are rendered from the actual model. See `validation.json` for structural export checks.

## Game integration

The original model in this folder is retained as asset source. From v0.9.14, `load-carrier.js` loads the redesigned assembled carrier in `../cargo_carrier_v2/`; see that folder's README for current integration and build instructions.

The procedural carrier remains visible until loading succeeds and serves as the fallback on missing or invalid assets. The new integration includes the Blender dish rig, normal maps, engine sprites, hangar force fields, and two distance-gated interior lights. Existing saves remain compatible.

Run `node assets/cargo_carrier_v2/build-game-assets.cjs` after rebuilding the active assembled GLB to refresh its direct-file copy. `node vendor/three-r158/build-loader.cjs` refreshes the vendored runtime and the active carrier payload. Browser integration checks are in `tests/carrier-integration.cjs`; results are saved in `tests/carrier-results.json`. `?debug` exposes `BeltRunner.carrierAsset` with revision, loading source, geometry counts, and material references.

Rebuild: run Blender in background with `--python build_carrier.py`. Validate with `--python validate_carrier.py`.
