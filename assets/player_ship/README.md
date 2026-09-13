# Belt Runner 3D — Player mining ship

Blender model based on the approved player-ship concept, with ImageGen panel textures baked into one shared 1024 x 1024 PBR atlas. The PNG set contains base color, metallic/roughness (G/B), tangent-space normal, and emissive. Lighting is computed by Blender Cycles or the game; it is not baked into the base color.

`player_ship.blend` contains the editable components, packed textures, chin-dish rig, camera and studio lights. Optional parts are hidden by default. `player_ship.glb` is Y-up, forward +Z, at the requested one-third modeling scale (about 26 long and 24 wide); use the game's x3 scale. All mesh rotations/scales are applied. Cameras and lights are excluded from the GLB.

The GLB has two scenes: `gltf.scene` is the complete default ship with delta wings and level-1 modules; `gltf.scenes[1]` is the alternate-component library. This prevents unused parts from stacking over the default ship. The included `assemble-player-ship.js` helper switches modules, attaches barrels to the moving dish, and updates nav-light and focus positions. The game now uses this helper through its generated classic-script version.

Required meshes: `wings_delta`, `wings_swept`, `wings_forward`, `wings_twin`; `laser_barrel_1..3`, `cargo_pod_1..3`, `engine_nacelle_1..3`, `scanner_dish_1..3`. Base meshes: `hull`, `hull_trim`, `emissive`, `canopy`, `cockpit_frame`, `cockpit`, `engine_core`, `dish_base`, `dish_yoke`, `mining_dish`. Exact per-mesh triangle counts and assembled totals are in `asset_report.json`. The assembled ship stays below 8,000 triangles; the complete library includes additional mutually exclusive parts.

Required empties: `dish_mount` at (0,-4.5,7), `engine_l`, `engine_r`, `nav_l`, `nav_r`. Red is game +X/left, green is -X/right. Additional rig empties: `mining_dish_yaw`, `mining_dish_pitch`, `focus`, `rim_0..5`. Rotate the yaw pivot about game Y through -90 to +90 degrees. The dish is supplied at player size as part of this model. The forward-swept wing has nav lights at a different Z; its `nav_l` and `nav_r` extras supply those positions.

Four independently controllable materials: `paint`, `trim`, `glass`, `emissive`. Tint `paint.color` in Three.js. The canopy uses physical transmission; front/rear preview PNGs show its Cycles appearance. The neutral ImageGen source is in `source/imagegen_panels.png`, with the exact prompt and approved concept. All deliverable texture PNGs are 1024 square. The normal map is derived by baking subtle bump from the ImageGen source; metallic/roughness and emissive maps are authored in Blender to match the real materials.

Preview PNGs include front, rear, all four wing plans, and level 3. `validation.json` records names, size, UV layout, export structure, triangle counts, and collision checks of the chin assembly through its forward yaw sweep.

The default assembly has 6,290 triangles; all 324 wing/upgrade combinations range from 6,290 to 6,570. The complete component library contains 11,058 triangles. Three.js r158 browser validation passed all 324 configurations, confirmed the dish rig and texture dimensions, and rendered the GLB without JavaScript errors; see `browser_validation.json` and `preview_threejs.png`.

Rebuild with Blender: `blender --background --factory-startup --python build_player_ship.py`. Validate with `blender --background --factory-startup --python validate_player_ship.py`.

## Game integration

The game's `buildShip()` configures the cached Blender model after it loads. Hull color tints the `paint` material; trim color replaces amber markings while preserving the dark structural panels. Three visual module tiers span each upgrade's existing level range; gameplay stats are unchanged. The model retains the game's x3 scale. Engine sprites and navigation beacons follow their named attachments. The mining dish uses its native Y-yaw/X-pitch rig, with the beam beginning at the selected barrel's focus point.

HTTP play loads `player_ship.glb`. Direct HTML opening uses `player_ship.data.js` to avoid local-file fetch restrictions. Run `node assets/player_ship/build-game-assets.cjs` from the project root after rebuilding the model or editing the assembly helper. Keep `assets` and `vendor` beside the game HTML. Missing assets retain the procedural player ship. `?debug` exposes `BeltRunner.playerAsset` and the loaded model.

`tests/player-integration.cjs` verifies 2,400 game-level/wing combinations, cached geometry, color controls, aiming, effects, departure and docking under HTTP and direct-file loading, plus missing-model fallback. Results are in `tests/player-integration-results.json`; `in-game.png` shows the integrated player ship on a hangar pad.
