# Cargo carrier redesign

Blender reconstruction of the supplied Cargo Carrier concept for Belt Runner 3D. Pale weathered armor, beveled transverse frames, a tapered prow, warm service windows, three recessed engine bells, and a detailed through-hangar. The optional articulated dish is included in the assembled model and presentation scene.

This is the active carrier revision in the game from v0.9.14. The shared `../cargo_carrier/load-carrier.js` loader installs the assembled carrier and animated dish together after validation.

## Deliverables

| File | Purpose |
| --- | --- |
| `cargo_carrier.blend` | Editable meshes, packed textures, articulated dish, cameras, and Cycles lighting |
| `cargo_carrier.glb` | Carrier only: four meshes/materials and 13 game attachment points |
| `mining_dish.glb` | Separate dish with yaw/pitch hierarchy and focus/rim anchors |
| `cargo_carrier_assembled.glb` | Complete carrier and dish in their assembled pose |
| `cargo_carrier_assembled.data.js` | Generated copy of the assembled binary for direct disk play and hosts without GLB support |
| `textures/` | Shared 2048 × 2048 base color, metallic/roughness, tangent normal, and emissive PNGs |
| `previews/preview_front.png`, `previews/preview_rear.png`, `previews/preview_profile.png` | Actual Blender Cycles exterior renders |
| `previews/preview_hangar.png` | Cycles view through the modeled hangar |
| `previews/preview_threejs.png` | Actual browser render using the game's Three.js r158 dependencies |
| `previews/in-game.png`, `previews/in-game-hangar.png` | Captures from the integrated game with its own lighting |
| `source/` | User reference, both ImageGen source textures, and generation prompts |
| `asset_report.json`, `validation.json`, `browser_validation.json` | Geometry, attachment, UV, clearance, and loading results |

The carrier uses 35,316 triangles; the assembled carrier and dish use 37,496. The four carrier mesh/material names are `hull`, `interior`, `emissive`, and `glass`. Windows use opaque emissive glazing for the existing game material contract.

## Coordinates and materials

Exports use Y up, forward +X, and one Blender meter per game unit. The carrier spans X −3550 to +4600 (8150 total). Its principal hull envelope is 1800 wide and 1080 high; bridge equipment, beacons, conduits, and the existing drone docking arms extend beyond that envelope. All 13 carrier anchor coordinates match the original asset and are listed in `asset_report.json`.

The structural hangar opening spans X ±420 and Y ±176 on both Z flanks. Decks, ceiling lights, wall equipment, and the cargo sign sit inside the structural opening; the tested central flight corridor is clear in both directions. Pads and cargo-drop anchors retain their original positions.

The reference sheet contains conflicting rear engine sketches. Three engines are retained to match its written specification and the current game attachment contract.

The dish GLB preserves its assembled world position: its yaw origin is at the carrier's `dish_mount` point. Its pitch pivot, `focus`, and six `rim_*` markers form an articulated hierarchy. Load it alongside the carrier at the same scene origin; do not add the mount offset twice. The assembled GLB already includes it.

Both ImageGen textures are projected onto modeled surfaces and baked in Blender into a single UV atlas. Base color and emissive maps use sRGB; normal and metallic/roughness maps use linear data. Metallic/roughness follows glTF channels: green = roughness, blue = metalness. The normal map is baked from surface bump derived from the source textures. The GLBs embed all four PNGs and exclude presentation lights/cameras.

The game retains the normal maps and uses the zone's sun, fill, sky light, and environment reflections. The two existing hangar lights are warm and positioned below the modeled ceiling, with distance gating preserved. The Blender studio's additional lights stay in the source scene.

The runtime loads the assembled GLB once, sharing its four textures between the hull and dish. A control pivot removes the dish's authored presentation tilt so yaw and pitch still aim along local +X. Mining rays start at the actual focus marker; the six rim glows and charging beams follow the model's emitters. Engine and warp glows, bay force fields, drone docks, parking pads, and cargo-drop coordinates retain their game behavior. The duplicate procedural turret and cargo sign are removed after successful installation. Missing or invalid assets leave the procedural carrier usable.

HTTP play loads the binary directly. Direct disk play, and HTTP hosts that reject GLB, load the generated JavaScript payload containing the same bytes. Keep the `assets` and `vendor` folders beside `belt-runner-3d.html`. Existing saves remain compatible.

## Rebuild and verify

Run from the repository root with Blender 5.2:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python assets/cargo_carrier_v2/build_carrier.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python assets/cargo_carrier_v2/validate_carrier.py
node assets/cargo_carrier_v2/build-game-assets.cjs
node tests/cargo-carrier-v2-assets.cjs
node tests/carrier-integration.cjs
```

The browser verification uses the local Codex runtime's Playwright installation and installed Chrome. Asset checks load all three GLBs, check materials/anchors, ray-test the hangar, and render the assembled ship. The Blender validator additionally checks triangle counts, a single non-overlapping UV channel, embedded 2048-pixel PNGs, 70 passage rays, packed Blender textures, and the dish rig. The integration checks exercise normal HTTP loading, direct disk loading, HTTP script fallback, missing/corrupt model fallback, mining alignment and effects, docking through both mouths, and a warp to another belt. Results are in `../../tests/carrier-results.json`.
