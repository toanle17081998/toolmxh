# Construction-brick physics simulation video

> The studio now supports many content families, design comparisons, outcome-driven revisions, impacts, bridge tests, balls and dominoes. See [SIMULATION_CONTENT_FRAMEWORK.md](SIMULATION_CONTENT_FRAMEWORK.md) for the current catalog, API, examples and verification evidence. The original course/prototype below remains the first physics milestone.

## What changed

The canonical mode is `physics_simulation_video` (`PHYSICS_SIMULATION_VIDEO` also accepted by the API). Existing `simulation_video` requests/project configs are normalized to it. Short Content remains the default and continues to use its own Vietnamese script, TTS, subtitles, visual providers and FFmpeg pipeline.

The new primary renderer is **Blender Bullet physics**, not an AI video model. The old support-height/root-translation scene is retained as historical code but is disabled by the application renderer. Existing AI providers remain available to Short Content.

## Verified first milestone

- `outputs/physics_prototype_v2/prototype.mp4`: 10 seconds, 480×270, 30 fps, 300 decoded frames. A red studded construction-brick crawler drives off a high platform, pitches nearly 90 degrees, flips and lands upside down. Four physical wheels and a full-body collision proxy remain attached to unchanged visual geometry. Frames at 105/125/200 were inspected.
- `outputs/physics_mvp_42/final.mp4`: 20 seconds, 480×270, 30 fps, 600 decoded frames, two independent 10-second render segments, SFX. Seed 42 generates platform drop → ramp → stairs → gap. Extracted `acceptance_*.png` and `physics_acceptance.json` accompany the MP4.
- The measured course covers approximately 42.33 units. Each wheel rotates approximately 92–95 radians (expected travel/radius ≈92 radians). Initial two-segment telemetry prefixes were exactly equal. The vehicle is not keyframed along an invented path.

The large-drop prototype intentionally demonstrates a failure; the gentler production sample demonstrates progressing through all four obstacles. It does not force a flip in every course.

## Local dependencies / run

Python 3.10+, the existing `requirements.txt`, Blender **4.5 LTS**, and FFmpeg with H.264/AAC. FFmpeg is discovered using the existing PATH/imageio-ffmpeg fallback. Install Blender separately from https://www.blender.org/download/lts/4-5/.

```powershell
python -m pip install -r requirements.txt
python -m app web
python -m app.simulation --duration 20 --segment-seconds 10 --quality preview --seed 42 --project-id physics_mvp_42 --keep-scenes
python tests/verify_physics_sample.py physics_mvp_42
```

Use a **new project ID** to change its configuration. Reusing an ID honors its persisted configuration/scenario. `--resume --project-id ...` and the existing API/UI resume actions reuse compatible completed segments. Pre-refactor animated scenarios require a new project rather than being silently relabeled physical.

### Environment

| Variable | Purpose |
|---|---|
| `BLENDER_PATH` | Executable path, or leave empty when Blender is on PATH |
| `BLENDER_RENDER_ENGINE` | `BLENDER_EEVEE_NEXT` (supported GPU/headless graphics context) or `CYCLES` (CPU supported) |
| `BLENDER_TIMEOUT` | Process timeout in seconds; default 7200 |
| `BLENDER_MAX_PARALLEL_JOBS` | Concurrent Blender processes per app process; default 1 |
| `BLENDER_SEGMENT_RETRIES` | Existing retry limit; default 2 |
| `BLENDER_CLEANUP` | Remove successful PNG/.blend temporary assets; keep false for inspection |
| `PROJECTS_DIR`, `OUTPUTS_DIR` | Existing persisted project/export paths |

Commands are argument arrays with `--background --factory-startup --python-exit-code 1`; no shell interpolation or embedded OS-specific installation paths. Blender stdout/stderr and FFmpeg logs are retained.

## API

```json
{
  "video_type": "physics_simulation_video",
  "simulation_type": "brick_vehicle_obstacle",
  "vehicle": "brick_crawler",
  "duration": 20,
  "difficulty": "progressive",
  "aspect_ratio": "16:9",
  "theme": "minimal_gray_track",
  "camera_style": "dynamic_follow",
  "quality": "preview",
  "sound": "sfx_only",
  "seed": 42
}
```

POST `/api/generate`; poll `/api/progress/{id}`; POST `/api/resume/{id}` or `/api/regenerate/{id}/{segment}`; download `/media/{id}/artifact/final.mp4`.

Duration schemas/planning accept 20–1800 seconds, including 30/60/180/300/600/1200/1800. **Real-render evidence currently covers 10/20-second previews only.** Longer runs can fail validation on uncontrolled obstacles; do not interpret enabled duration planning as validated long-form production readiness. Start with Preview. Quality is preview (480×270), standard (1280×720), high (1920×1080), swapped in portrait mode. Legacy `draft`, `brick_basic_car` and `colorful_toy_world` normalize to preview-compatible quality/canonical crawler/gray theme. Legacy audio booleans remain supported; `sound` explicitly overrides them.

Camera modes: dynamic follow, follow, side follow, low follow, front obstacle, top down, static. The tested default is a readable side-quarter follow. Additional modes/aspects require visual validation on target hardware.

## Physics / rendering architecture

```text
Existing project/background job infrastructure
  → ScenarioGenerator → SimulationDirector → SimulationTrackGenerator
  → BrickVehicleFactory + obstacle plugins + passive track colliders
  → active Bullet chassis + four cylinder wheels + hinge and motor constraints
  → sequential fast physics validation → fingerprinted telemetry cache
  → fresh Blender process → measured-transform playback / camera / lighting
  → bounded PNG render segments → FFmpeg H.264
  → measured impact SFX + optional original procedural music → final MP4 / decode QC
```

Wheel motors target `speed / radius`; contact friction supplies translation. Gravity and collisions determine body position and orientation. No `car.location.x += speed` driving. Decorative bricks/studs/plates/beams/axles/hubs/treads are rigidly attached to their solved chassis or wheel. A hidden body proxy covers the brick assembly, including upside-down contacts. Wheels are independent physical bodies connected by hinges; motor local X and hinge local Z align with the vehicle axle (world Y).

The simulation process records position/quaternion samples, obstacle-crossing diagnostic checkpoints and impact events. Validation rejects non-finite/extreme transforms, leaving the track, collider penetration bounds, no progress and four seconds of being stuck. Failed validation prevents render/FFmpeg execution. Retries currently recompute the same scenario; automatic recovery/parameter adjustment is not yet implemented.

Rendering **keyframes the measured physics results**, not an analytically invented driving path. This hybrid playback is necessary for reliable random frame access and bounded independent rendering. Removing already-simulated constraints and rendering in the same Blender 4.5 process caused a Bullet access violation; the verified workflow uses a fresh playback process.

The physical trajectory is simulated once per fingerprint and shared by all render segments. This avoids cumulative from-origin re-simulation for every segment. Fingerprints include physics scene/vehicle/primitives/camera/obstacle source, input track/config and Blender version. Changed fingerprints invalidate rendered segment caches; compatible retries/resume reuse the authoritative trajectory. Rendering stays bounded to at most 30 seconds. The current trajectory cache/track geometry still scale with whole-video duration; streamable simulation blocks and resource tests remain future work.

Measured positions/quaternions/body samples are stored in segment world-state/checkpoint metadata. They are diagnostic snapshots, **not a verified velocity-restoring Bullet checkpoint API**. Recovery currently means retrying/replaying a compatible cached trajectory, not continuing a fresh solver from an arbitrary obstacle frame.

Encoded MP4 cache identity additionally includes render engine, quality, dimensions/aspect ratio and segment bounds. Changing render settings invalidates encoded segments while compatible physics telemetry remains reusable. Static camera anchors use the full trajectory's initial position across segment boundaries.

## Obstacles and assets

MVP plugins: `PlatformDropObstacle`, `GapObstacle`, `RampObstacle`, `StairsObstacle`. Straight runway spans are generated between sections. Drop/gap geometry really removes upper support; no continuous collider fills the opening. Plugins use `createGeometry`, `configurePhysics`, `configureAnimation`, entry/exit, validation and cleanup. Existing rotating bar/hammer/moving platform plugins remain extension code but are not selected by the physics director. Remaining requested mechanisms are not advertised as implemented.

Order currently cycles drop/ramp/stairs/gap with seeded dimensions/spacing, bounded repetition and difficulty metadata. Rich retention direction, randomized order, suspension, steering, six-wheel vehicles, seesaws/crushers/collapsing bridges and other simulation types are future extensions. The framework separates planning, vehicle/obstacle creation, solving, playback, camera, sound and composition.

All current geometry/audio are original procedural assets, with no protected branding or external asset dependency. Optional LDraw loading can be added behind the vehicle factory. Before shipping imported assets, document exact model/part URLs, creator, license/attribution/redistribution requirements; an importer's license does not license its imported models. LDraw is not required for MVP.

## Tests and evidence

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app tests
python tests/verify_physics_sample.py physics_mvp_42
python tests/dashboard_smoke.py http://127.0.0.1:7861
```

`verify_physics_sample.py` checks the actual video decode, four wheel bodies, measured rotation/travel, trajectory consistency and extracts frames from the final MP4. Unit/integration tests cover mode aliases, absence of short-factory calls for simulation, pre-render validation failure, queue/persistence/resume/concurrency, FFmpeg composition and existing Short Content dispatch/storage/relevance contracts. Those tests are not a paid/networked end-to-end Short Content render.

Existing jobs are in-process FastAPI BackgroundTasks with project leases. Parallel render limits are per process, and segments currently render sequentially within a project. Distributed queue/GPU Docker deployment and cross-process render limits remain future infrastructure; no separate application was created.
