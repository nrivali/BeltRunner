# Continuous cutscene cameras

The Hub approach inherits the final warp camera position, look target, and up direction. It moves around the carrier at a safe distance and ends on the same composition as the holding-station view. The cinematic bars remain active across the warp handoff.

Hangar approaches and departures inherit the current view, travel beside the ship through the open passage, and ease into the parked or flight camera. The ship's existing straight-through docking path, hover, descent, and controls are unchanged.

A return from warp to a belt covers the exterior view over 0.35 seconds, changes to the hangar while fully covered, then reveals the interior over 0.5 seconds. Space skips this fade with the warp. No extra 3D render passes or textures are needed.

`camera-shots.js` contains the shared camera paths. `tests/cinematic-transitions.cjs` checks each frame of the colony approach, both hangar directions, camera clearance through the passage, state cleanup, cargo/upgrades, and Space skips. It also verifies that the exterior-to-interior camera change is fully covered. `validation.json` records the exact tested source hashes and movement measurements; `previews/` contains game-renderer captures.
