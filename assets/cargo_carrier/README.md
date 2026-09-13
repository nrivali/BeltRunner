# Belt Runner 3D — cargo carrier

Blender 5.2 model with Cycles studio renders. Export: Y up, forward +X, game-unit scale, four mesh/material groups, embedded 2048 PNG PBR atlas, one UV set, triangulated geometry. Lighting and camera are retained in the Blender scene only.

Meshes: `hull`, `interior`, `emissive`, `glass`. Empties: `hangar_mouth_pos`, `hangar_mouth_neg`, `pad_pos`, `pad_neg`, `drop_pad`, `dish_mount`, `engine_0`, `engine_1`, `engine_2`, `drone_dock_0`, `drone_dock_1`, `drone_dock_2`, `bridge_windows`. Triangle count and exact coordinates: `asset_report.json`.

The mining dish is the separate asset 4; this carrier includes its mast and attachment point. Window glass uses opaque luminous panes for predictable browser rendering. Surface details are geometry; the supplied normal atlas is neutral. Metallic/roughness texture uses glTF channels: G roughness, B metallic. Shared texture atlases have individual padded polygon islands.

Preview files: `preview_front.png`, `preview_rear.png`, `preview_hangar.png`. These are rendered from the actual model. See `validation.json` for structural export checks.

## Game integration

`belt-runner-3d.html` loads the GLB through `load-carrier.js`, using the locally vendored Three.js r158 loader and runtime. HTTP play fetches the binary directly. Opening the HTML as a local file loads `cargo_carrier.data.js`, a generated copy of the same binary, to avoid browser restrictions on local file fetches. Keep the `assets` and `vendor` directories beside the game HTML.

The original carrier remains visible until loading succeeds and serves as the fallback on a missing or invalid model. Successful loading replaces its static geometry while retaining the animated mining dish, engine sprites, hangar force fields, and two distance-gated interior lights. Named attachment points position docking paths, the dish, drone docks, and engines. Ships park 38 units above the pad surface markers; collision uses the actual floor height. Existing saves are compatible.

After rebuilding the GLB, run `node vendor/three-r158/build-loader.cjs` from the project root to refresh the direct-file copy. Browser integration checks are in `tests/carrier-integration.cjs`; results are saved in `tests/carrier-results.json`. `?debug` exposes `BeltRunner.carrierAsset` with loading status and material references. Tests exercise HTTP, direct-file loading, missing-file fallback, and docking through both mouths. Overall game performance remains hardware-dependent.

Rebuild: run Blender in background with `--python build_carrier.py`. Validate with `--python validate_carrier.py`.
