# Sun and lighting — v0.9.25

The approved concept is implemented through a compact white solar disk, localized optical glare, strong directional sunlight, subdued neutral fill, dark space, and sharper metallic reflections. The seven zones retain their distinct warmer or cooler stars. The source follows the camera at a constant direction and angular size; planets, carrier hulls and asteroid surfaces occlude its glare.

Nearby ships, rocks and scenery cast and receive PCF shadows. A stabilized orthographic shadow camera follows the view, with a wider coverage area near the carrier. Nearby off-screen asteroid casters remain in the shared batches. Low, Balanced and High use 1024, 2048 and 4096 shadow maps respectively. Distant asteroids retain their existing lower-detail meshes. Large-scale planetary eclipses are evaluated in the material shader, outside the local shadow map. The atmospheric limb is strongest on the planet's sunlit side.

The two existing hangar lights now illuminate the interior with warm reflected light. ACES exposure protects bright hull and ore highlights. Environment reflections use a dark neutral background with the solar source aligned to the same direction as the direct light. Zone changes dispose of the previous PMREM render target.

This remains a real-time browser lighting system: local shadow maps and an environment map approximate the concept's rendered look. It does not add path tracing or a full-scene bloom pass. No textures, models, ore balances, controls or ship mechanics were replaced.

Validation:

```powershell
node tests/lighting-integration.cjs
node tests/lighting-integration.cjs --file
node tests/asteroids-v2-integration.cjs
node tests/carrier-integration.cjs
```

The lighting test renders the carrier, ore surfaces, sun and hangar, then samples actual framebuffer pixels to verify local cast shadows and planetary eclipses. It renders every zone and all quality settings and rejects shader or page errors. Screenshots and reports are stored alongside this file. Regression checks cover held-trigger mining, heat, fragments, collisions, docking, warp and asset delivery fallbacks.

The work started after Claude's `e286e03` hold-to-fire commit. His subsequent `75075a8` free-firing beam and `b6fd717` laser distance-falloff changes, and his `bb2b8ae` range HUD, were preserved before the final lighting version bump. File hashes and immediate pre-edit backup locations are recorded in `change-proof.json`.
