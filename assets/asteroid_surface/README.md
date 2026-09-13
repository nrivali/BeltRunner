# Asteroid surface texture

`asteroid_albedo.png` is the original 1254 × 1254 image generated with the built-in ImageGen tool. The exact prompt is in `imagegen-prompt.txt`.

`load-rock-texture.js` shares this texture across barren, faceted, smooth, and cave asteroid materials. Object-space triplanar projection keeps the detail attached to rotating rocks and avoids stretching around UV poles. PBR materials use roughness 0.92, metalness 0.025, and surface perturbation derived from the sampled mineral detail. Small barren rocks retain their inexpensive Lambert material. No geometry or draw calls are added.

The existing ore vein field is retained without the old spot flecks, with restrained ore color and emission. Mining heat callbacks and cloned damaged-rock materials retain their effects. Zone colors continue to update the same shared materials.

HTTP play loads the PNG. Direct file play loads the data URL in `asteroid_surface.data.js`; regenerate it with `node assets/asteroid_surface/build-game-assets.cjs` after changing the source PNG. Failed image loading leaves the original procedural textures in place.

`tests/rock-surface-integration.cjs` verifies HTTP, file loading, failure fallback, all four rock material families, shared texture use, heat shader preservation, and cloned material support. `before.png` and `in-game.png` show the same sample asteroid geometries under identical lights before and after loading the texture. They use the game's live geometries and materials in a comparison scene. `validation.json` contains the results.

The game HTML change adds three lines: the loader script, the heat-material hook, and texture initialization. Its immediate pre-edit backup is `backups/belt-runner-3d.before-rock-textures.2026-09-12T20-57-48-643Z.html`. The before SHA-256 was `9544bd39f8ead6bfb2a82f5315c1c7b6eb31f472d66581a0fe494940f00570f8`; after the three additions it was `177a61c82a73dae6b83742a7fcbc911cf9b3077585fbb2ff85774a2f394a8665`.
