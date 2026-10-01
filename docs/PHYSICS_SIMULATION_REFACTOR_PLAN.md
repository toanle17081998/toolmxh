# Physics simulation refactor plan

## Audit — 2026-10-01

Working tree was clean before this audit. No AGENTS.md is present. This is a Python/FastAPI application with filesystem project state, in-process background jobs and a plain HTML dashboard, not a Laravel application.

`23c89ca` added Wan/LTX/Hunyuan providers to **Short Content**. The simulation package was originally added in `2dabb3a`, with subsequent changes in `1918b06` and `f14d45f`. There is no `REALISTIC_AI_SIMULATION` enum in this checkout. Do not remove shared AI providers: Short Content still uses them.

### Current implementation → incorrect assumptions

- `app/simulation/blender_scene.py:74-84` sets `x = time * speed`, obtains a height profile and keyframes the entire vehicle.
- `app/simulation/vehicle.py:15-16,40-47` makes the chassis kinematic, animates the root and rotates wheels from elapsed time rather than measured travel. Gravity and collisions cannot affect vehicle motion.
- `app/simulation/blender_scene.py:41-46` creates an uninterrupted runway. A gap/drop cannot work while that collider remains beneath it.
- `app/simulation/obstacles/base.py:15-18` defaults even static obstacles to animated bodies.
- `app/simulation/scenario.py:30-46` predicts segment poses analytically; those are not physical end states.
- Config/API/UI expose basic car, colorful world, 30–180 seconds, draft quality and music on by default. Documentation explicitly describes animated traversal, not solved vehicle dynamics.
- Useful infrastructure already exists: portable configured Blender executable, process limits/timeouts, isolated attempts, persisted retry/resume, FFmpeg encoding/concatenation, media validation and downloads. Configured Blender and bundled FFmpeg are available even though neither is on PATH.

## KEEP

| Files | Reason |
|---|---|
| `app/factory.py`, `app/providers/**` | Existing Vietnamese script/voice/subtitles/assets pipeline, including AI video providers |
| `app/core/state_manager.py`, `app/simulation/lock.py` | Atomic persisted state and project ownership |
| `app/simulation/blender_renderer.py` process runner | Timeout, cancellation, logs, concurrency, isolated render attempts |
| `app/simulation/media.py`, `app/engines/composer.py` | Strict decoding QC, segment encoding/composition |
| `app/simulation/audio.py` | Original procedural audio, chunked memory usage |
| `app/simulation/geometry.py`, `camera.py` | Reusable primitives/material cache and follow-camera infrastructure |
| Existing dashboard/API/CLI progress and storage routes | Additional mode inside this application |

## REFACTOR

- Replace kinematic vehicle driving with active chassis/wheels, axle hinge constraints and motor torque. Parent decorative bricks only to their physical chassis/wheel, never animate the physical chassis forward.
- Add reusable studded brick/plate/beam/axle/connector primitives and a four-wheel red `brick_crawler`.
- Bake/sample the physical simulation first; validate transforms, progress, drop, pitch and collisions before rendering. Camera follows measured transforms.
- Build discontinuous collision geometry for platform drops and gaps. Static colliders are passive; motor obstacles may remain deterministic.
- Rename canonical video mode to `physics_simulation_video`, preserving `simulation_video` as a legacy input alias. Add simulation type `brick_vehicle_obstacle`, preview quality and SFX-only defaults.
- Replace analytic continuity with actual transform/velocity checkpoint data. Until this is verified, do not claim physical segment continuity or enable long-form production presets.
- Extend track generation only after the platform-drop prototype works. Seeded selection and anti-repeat machinery remain reusable.

## REMOVE / DISABLE FROM THIS MODE

- Root translation and support-height fake driving (`vehicle_pose`) as the primary physics engine.
- Uninterrupted runway beneath gaps/drops; unverified success cues and predicted landing audio.
- AI provider, reference-frame/I2V, TTS and subtitle requirements (already absent from simulation service; preserve that separation).
- No shared provider files or unrelated application features are scheduled for deletion.

## ADD

1. Standalone 10-second prototype: studded brick crawler, exactly four physical wheels, motor hinges, elevated platform, lower landing, gravity, measured-camera follow and low-resolution MP4.
2. Simulation telemetry and fast validation with failure reports before expensive rendering; visual frame extraction.
3. PlatformDrop and Gap obstacle plugins; passive ramp/stairs physics.
4. Generic `BlenderSimulationRenderer`, `BrickVehicleFactory`, director and actual `SimulationWorldState` handoff once verified.
5. MVP 20–30-second preview and regression evidence.

## Execution gates (strict order)

1. Audit and save this plan **before changing implementation**.
2. Prototype and render approximately 10 seconds. Inspect frames: brick identity, four wheels, moving wheels, front-wheel support loss, tilt, fall and landing. Fix physics before integration.
3. Integrate verified engine into existing workers/storage/API/UI; keep Short Content dispatch intact.
4. Add seeded straight/drop/ramp/stairs/gap course and render 20–30-second preview at 30 fps.
5. Run meaningful regression tests and decode actual MP4. Document exact evidence and limitations; no completion claim from Blender exit status alone.

## Physics and operational decisions

Use Blender Bullet active rigid bodies with high solver iterations/substeps, chassis compound-looking decorative geometry on a simple collision proxy, four independent cylinder wheel colliders, hinge joints and motor constraints. Axle direction is local Y; hinge/motor local Z must align with it. Ground friction provides propulsion. Gravity/contacts determine translation and body rotation. Deterministic keyframes are reserved for obstacle mechanisms and camera, or playback of **previously simulated** measured transforms.

Physics should be simulated sequentially before rendering; arbitrary frame jumps do not reliably evaluate an unbaked Bullet world. Record physics telemetry separately from scene rendering. Cache/replay telemetry only when configuration/version fingerprints match. Stuck detection should report failure and later permit explicit checkpoint recovery, not silently translate the car.

Headless execution uses configured `BLENDER_PATH`, `BLENDER_RENDER_ENGINE`, `BLENDER_TIMEOUT`, `BLENDER_MAX_PARALLEL_JOBS`; never embed an installation path. Preview first. Reuse bundled FFmpeg discovery. Current job system remains in-process, not a distributed queue.

## Assets / licensing

MVP geometry and audio are original procedural assets with generic construction-brick names; no branded meshes/textures. Optional LDraw import can fit behind a vehicle loader, but is deferred. Before enabling it, record the exact model/part source, creator, applicable LDraw library license and redistribution/attribution terms (library and third-party models may differ); an importer license does not license imported models. No external LDraw assets are currently needed.

## Acceptance and reporting

Report all files changed, prototype/MVP MP4 paths, extracted frames, telemetry, test commands, local run instructions and missing gates. Existing tests verify legacy request/dispatch/storage contracts; a real Short Content render needs configured network providers and must not be represented as tested by mocks.

## Executed milestone / handoff

- Audit and this plan were written before implementation.
- Real 10-second prototype: `outputs/physics_prototype_v2/prototype.mp4`, 300 frames. Inspected brick construction, four wheels, support loss, near-90-degree pitch, natural flip and upside-down landing. Collision proxy was corrected after early visual inspection found cosmetic-body penetration.
- Real 20-second MVP: `outputs/physics_mvp_42/final.mp4`, 600 frames, 480×270, 30 fps, SFX, two 10-second render segments. Final decoded size 960011 bytes. Telemetry: 42.3267 units travel; wheel angular travel 92.69/92.26/94.36/95.12 rad; four checkpoints and two measured landing sounds. MP4-extracted acceptance frames inspected.
- Unit/integration suite: **39 tests passed**. Includes existing Short Content dispatch/storage/relevance coverage; no full networked Short Content generation was performed.
- Browser smoke passed against the real dashboard: mode switching, canonical request, segment progress, resume and Short Content settings restoration.
- `tests/render_smoke.py` rendered actual crossing samples for platform_drop/ramp/stairs/gap; all decoded correctly.
- User-reported startup enum mismatch traced to an old process on port 7860 serving the original enum. Restarted application server and verified live OpenAPI accepts `physics_simulation_video`.
- Review corrections: canonical UI aliases, input alias normalization, whole-trajectory cache, source/Blender/config fingerprints, separate render fingerprints, measured orientation, authoritative event replacement, non-bouncing landing detection, prototype playback gate and static-camera seam anchor.

### File inventory for this refactor

**Kept/reused:** `app/core/state_manager.py`, `app/engines/composer.py`, `app/simulation/{audio,camera,geometry,lock,media,selection}.py`, existing config/FFmpeg discovery, background jobs, download routes. AI provider infrastructure remains available for Short Content.

**Refactored:** `app/models/project.py`, `app/web/server.py`, `app/web/templates/index.html`, `app/simulation/{__main__,models,scenario,track,blender_renderer,service}.py`, `app/simulation/obstacles/{base,__init__}.py`, `tests/{test_simulation_api,test_simulation_pipeline,test_simulation_planning,dashboard_smoke,render_smoke}.py`, README and prior simulation docs (marked historical).

**Added:** `app/simulation/{physics_vehicle,physics_scene,physics_prototype,director,fingerprint}.py`, `app/simulation/obstacles/{platform_drop,gap}.py`, `tests/{test_physics_mode,verify_physics_sample}.py`, this plan and `docs/PHYSICS_SIMULATION_VIDEO.md`.

**Removed:** no files. The old `blender_scene.py`/`vehicle.py`/`motion.py` animated traversal is disabled from application rendering; legacy stored animated scenarios must start a new physics project.

### Remaining scope

The completed milestone is the physical 10/20-second MVP, not the full future specification. 30-minute settings/planning exist but long renders are not validated. Steering/suspension, automatic stuck recovery, velocity-restoring checkpoints, advanced retention/random obstacle order, additional vehicles/mechanisms/simulation types, distributed queues and GPU Docker workers remain future work. Current retries use the same scenario; stuck validation prevents wasting final render time but does not guarantee every seed succeeds. The trajectory cache and full track geometry still grow with total duration, though render scenes are frame-bounded.
