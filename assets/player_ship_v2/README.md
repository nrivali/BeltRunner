# Rounded player mining ship

The approved mining-skiff concept rebuilt in Blender, with a curved pressure hull, panoramic glazed cockpit, rounded twin engine housings, graphite service panels, compact winglets, and an articulated chin mining tool. The canopy has a real opening in the hull and a modeled seat, restraints, consoles, and instruments underneath it.

## Assets

- `player_ship.blend`: editable source model with packed images, upgrade parts, mining rig, Cycles lighting, and presentation camera.
- `player_ship.glb`: default assembled ship plus a separate scene containing interchangeable components. Textures are embedded; presentation lights and cameras are excluded.
- `player_ship.data.js`: matching base64 export for direct-file play and binary-loading fallback.
- `preview.html`: interactive orbit view with cockpit, engine, and tool close-ups, all four wing choices, three visual tiers, hull color, and dish motion.
- `previews/`: Blender renders and browser captures of the actual asset.
- `source/approved_concept.png`: approved concept. `source/imagegen_panels.png`: new neutral hull texture generated with **built-in ImageGen**. Exact prompts are in `source/imagegen-prompts.json`.
- `textures/`: 4096 × 4096 base color; 2048 × 2048 normal, metallic/roughness, and emissive maps baked in Blender. The ImageGen source is 1254 × 1254; the 4K atlas provides UV space for all components, rather than implying 4K detail in the original scan.

The paint atlas is neutral to preserve the game's hull-color customization. Material roughness, metal response, emissions, and subtle surface normals are authored and baked separately; sunlight and reflections are computed when rendered. The canopy uses physical transmission with a subtle warm tint. Blender renders use Cycles and AgX; the browser preview uses the game's lighting system.

## Game interfaces

All 26 existing component names are retained, including four wing plans and three variants each for laser, cargo, engine, and scanner upgrades. The assembly helper switches cached components without loading new geometry. Hull and accent colors remain customizable. No upgrade prices, statistics, movement controls, inventory, or mining rules are changed.

The ship is +Z forward, +Y up, at the existing one-third modeling scale; the game uses scale 3. All configurations fit the existing 16-unit asset-space collision envelope. The new curved geometry uses fewer than 24,000 triangles in any assembled configuration. Exact totals are in `asset_report.json`. This is more geometry and texture memory than the former ship, spent on the visible curved cockpit, hull, and engines; only one configuration is drawn at a time.

The mining mount is `[0,-3.4,7]`. Its reflector axis sits farther forward within the short fork to clear the support throughout the existing yaw and pitch limits. The helper preserves the selected barrel's focus offset. Engine anchors are `[4.55,1.45,-12.87]` and `[-4.55,1.45,-12.87]`; wing variants supply their own navigation-light positions. The game's loader reads those markers instead of relying on the old geometry's positions.

`load-player-ship.js` uses the new versioned asset directory and retains the procedural fallback if loading fails. Game integration changes only the assembly-helper URL, model-loader URL, and build number. `change-proof.json` records the source commit, backup, and before/after hashes when integration is applied. Publication is separate from the local asset commit.

## Rebuild and verify

From the repository root:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python assets/player_ship_v2/build_player_ship.py
node assets/player_ship_v2/build-game-assets.cjs
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python assets/player_ship_v2/validate_player_ship.py
node tests/player-v2-preview.cjs
node tests/player-v2-integration.cjs
```

`build_player_ship.py` is standalone. `geometry.py` and `assemble_builder.cjs` preserve the derivation from the previous ship pipeline. Rebuilding does not require rerunning the integration script. Blender writes Python assertion failures to the log even when its process returns zero, so check for the `VALIDATION` success record and `validation.json`.

Blender validation checks embedded maps, UV overlap, component structure, collision envelope, and 555 mining-tool poses: three barrels, 37 yaw angles, and five pitches spanning the game's full range. Browser validation checks all 324 visual configurations, custom paint, views, and controls. Game integration checks 2,400 upgrade/wing combinations per successful loading mode, laser aiming and focus, exhaust/navigation effects, docking, and HTTP/direct-file/script/missing/invalid loading. Results and exact game/model hashes are stored alongside the assets. The preview test expects the workspace server on port 49280; integration tests create their own local server.

`integration-history.json` records the observed passing functional checks in all five loading modes, followed by a failed source-stability guard when concurrent inventory work changed the shared HTML. `final-smoke-validation.json` records the subsequent normal-loading, customization, aiming, and docking checks against the final ship-integration source. The records distinguish those checks from a complete five-mode run on a single final version.
