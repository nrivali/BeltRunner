# Cargo carrier redesign

Blender reconstruction of the supplied Cargo Carrier concept for Belt Runner 3D. Pale weathered armor, beveled transverse frames, a tapered prow, warm service windows, three recessed engine bells, and a detailed through-hangar. The optional articulated dish is included in the assembled model and presentation scene.

This folder is a separate asset revision. The live game's carrier model and loader have not been replaced.

## Deliverables

| File | Purpose |
| --- | --- |
| `cargo_carrier.blend` | Editable meshes, packed textures, articulated dish, cameras, and Cycles lighting |
| `cargo_carrier.glb` | Carrier only: four meshes/materials and 13 game attachment points |
| `mining_dish.glb` | Separate dish with yaw/pitch hierarchy and focus/rim anchors |
| `cargo_carrier_assembled.glb` | Complete carrier and dish in their assembled pose |
| `textures/` | Shared 2048 × 2048 base color, metallic/roughness, tangent normal, and emissive PNGs |
| `previews/preview_front.png`, `previews/preview_rear.png`, `previews/preview_profile.png` | Actual Blender Cycles exterior renders |
| `previews/preview_hangar.png` | Cycles view through the modeled hangar |
| `previews/preview_threejs.png` | Actual browser render using the game's Three.js r158 dependencies |
| `source/` | User reference, both ImageGen source textures, and generation prompts |
| `asset_report.json`, `validation.json`, `browser_validation.json` | Geometry, attachment, UV, clearance, and loading results |

The carrier uses 35,316 triangles; the assembled carrier and dish use 37,496. The four carrier mesh/material names are `hull`, `interior`, `emissive`, and `glass`. Windows use opaque emissive glazing for the existing game material contract.

## Coordinates and materials

Exports use Y up, forward +X, and one Blender meter per game unit. The carrier spans X −3550 to +4600 (8150 total). Its principal hull envelope is 1800 wide and 1080 high; bridge equipment, beacons, conduits, and the existing drone docking arms extend beyond that envelope. All 13 carrier anchor coordinates match the original asset and are listed in `asset_report.json`.

The structural hangar opening spans X ±420 and Y ±176 on both Z flanks. Decks, ceiling lights, wall equipment, and the cargo sign sit inside the structural opening; the tested central flight corridor is clear in both directions. Pads and cargo-drop anchors retain their original positions.

The reference sheet contains conflicting rear engine sketches. Three engines are retained to match its written specification and the current game attachment contract.

The dish GLB preserves its assembled world position: its yaw origin is at the carrier's `dish_mount` point. Its pitch pivot, `focus`, and six `rim_*` markers form an articulated hierarchy. Load it alongside the carrier at the same scene origin; do not add the mount offset twice. The assembled GLB already includes it.

Both ImageGen textures are projected onto modeled surfaces and baked in Blender into a single UV atlas. Base color and emissive maps use sRGB; normal and metallic/roughness maps use linear data. Metallic/roughness follows glTF channels: green = roughness, blue = metalness. The normal map is baked from surface bump derived from the source textures. The GLBs embed all four PNGs and exclude presentation lights/cameras.

For later integration, the existing carrier loader's `normalMap = null` override should be removed so this revision's surface detail is visible. Its separate dish loader/rig also needs to respect the hierarchy and coordinates above. Realistic studio and hangar illumination is authored in the Blender file; game lighting must be supplied by the renderer.

## Rebuild and verify

Run from the repository root with Blender 5.2:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python assets/cargo_carrier_v2/build_carrier.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python assets/cargo_carrier_v2/validate_carrier.py
node tests/cargo-carrier-v2-assets.cjs
```

The browser verification uses the local Codex runtime's Playwright installation and installed Chrome. It loads all three GLBs with the game's loader, checks materials/anchors, ray-tests the hangar, and renders the assembled ship. The Blender validator additionally checks triangle counts, a single non-overlapping UV channel, embedded 2048-pixel PNGs, 70 passage rays, packed Blender textures, and the dish rig.
