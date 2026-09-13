# Cargo hyperspace

Integrated in game v0.9.103. The carrier charges for 1.6 seconds, stretches forward and jumps in 0.45 seconds, travels through a blue tunnel for 2.45 seconds, then snaps into the destination and settles. Total duration: 6.25 seconds. Space skips any phase.

`hyperspace.js` owns the timeline and two procedural WebGL meshes: the tunnel and camera-space star ribbons. It uses fixed buffers, no texture downloads, 640 stars normally and 256 on low quality. Its scene group is hidden outside a jump. Reduced-motion preference removes flashes, hull stretch, and camera FOV changes, and reduces streak intensity and speed.

The game applies motion and stretch only to the rendered carrier. Dock anchors, collision positions, and orbital velocity remain independent. The destination loads once under the tunnel; completion and skip both restore the carrier, engine glows, camera, and UI. Hub arrivals continue into the existing colony approach; belt arrivals return to Dock 1.

Run `node tests/hyperspace.cjs` from the repository. The test uses local Chrome and the bundled Playwright runtime. It checks both live destinations, Space skips in all phases, docking, cargo/upgrades, cleanup, reduced-motion shader controls, quality limits, and visible star pixels. `validation.json` records the exact tested source hashes. `previews/` contains captures from the actual game renderer.
