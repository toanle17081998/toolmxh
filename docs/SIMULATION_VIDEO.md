# Simulation / Satisfying Video

> Historical pre-refactor documentation. The current physics engine, configuration, samples and limitations are documented in [PHYSICS_SIMULATION_VIDEO.md](PHYSICS_SIMULATION_VIDEO.md). The animated traversal descriptions below do not describe the active pipeline.

The app has two independent pipelines. `short_content` remains the default and uses the original Vietnamese script, TTS, subtitles and visual providers. `simulation_video` uses original Blender geometry, deterministic animation, procedural audio and FFmpeg. It does not construct the short-content factory or call AI/TTS services.

## MVP and limitations

The first simulation type is `vehicle_obstacle`: `brick_basic_car`, `colorful_toy_world`, `dynamic_follow`, and five plugins: ramp, stairs, rotating bar, swinging hammer and moving platform. Public creation supports 30–180 seconds, presets 30/60/180 and custom integer duration, in 16:9 or 9:16. The internal frame-based planner supports up to 1800 seconds without creating a large Blender scene. The CLI exposes that internal range for development; 5/10-minute and square output UI controls remain disabled pending longer render validation.

Vehicle motion and wheel rotation are deterministic keyframes. Track and obstacle collision bodies use Blender's rigid-body system with gravity, mass and friction; the vehicle and moving obstacles are kinematic for predictable completion. This is animated obstacle traversal, not a physically solved suspension/driving model. Crashes, flipping, cosmetic brick loss, weight-responsive seesaws, branching tracks and natural recovery choreography are deferred. `VehicleGenerator.recover` provides a checkpoint reset hook for future controlled failures. Render failures retry the affected segment; checkpoint records do not resume halfway through an individual Blender render.

The MVP camera follows a smooth rear-quarter/side orbit and preserves global time across segments. Additional camera modes, vehicle presets, obstacle types and environments are extension points rather than enabled features. Music and effects are original synthesized tones/noise, not a recorded foley library. Render cost depends on hardware and quality; a three-minute video can take much longer than three minutes to render.

## Requirements and installation

- Python 3.10+ and `pip install -r requirements.txt`.
- Blender **4.5 LTS**, installed separately. Download the installer or portable archive from [Blender](https://www.blender.org/download/lts/4-5/). Blender is not a Python pip dependency and does not need Pydantic installed inside its own Python.
- FFmpeg with H.264/AAC support. Existing `get_ffmpeg_binary()` uses PATH, then the imageio-ffmpeg bundle. ffprobe is not required: simulation QC fully decodes the video with FFmpeg.
- A working headless rendering device/context. Eevee normally needs a graphics driver; CPU-only environments can choose Cycles.

Copy `.env.example` to `.env`, then set `BLENDER_PATH` to your own executable. Paths containing spaces are supported; do not add embedded shell quotes. If Blender is already on PATH, leave it blank.

| Variable | Default | Meaning |
| --- | --- | --- |
| `BLENDER_PATH` | PATH lookup | Blender executable, absolute path or command |
| `BLENDER_RENDER_ENGINE` | `BLENDER_EEVEE_NEXT` | Eevee for Blender 4.5; optionally `CYCLES` |
| `BLENDER_TIMEOUT` | `7200` | Timeout in seconds for each Blender/FFmpeg subprocess |
| `BLENDER_MAX_PARALLEL_JOBS` | `1` | Maximum simultaneous Blender processes per application process |
| `BLENDER_SEGMENT_RETRIES` | `2` | Automatic retries after the first failed attempt |
| `BLENDER_CLEANUP` | `true` | Remove PNG frames and .blend files only after successful final export |
| `PROJECTS_DIR` / `OUTPUTS_DIR` | Existing app defaults | Project state/cache and exported artifacts |

Use portable storage paths in containers: e.g. `PROJECTS_DIR=/data/projects`, `OUTPUTS_DIR=/data/outputs`, `WORKSPACE_DIR=/app`, `ASSETS_DIR=/data/assets`. The original repository defaults point to its Windows development workspace.

## Local usage

Start the existing dashboard:

```bash
python -m app web
```

Select **Simulation / Satisfying Video**. Script/voice/provider settings disappear. Choose duration, output aspect, car color, difficulty, audio options, quality and optional seed. YouTube selects 16:9; TikTok/Shorts/Reels select 9:16. The existing preview and MP4 download flow is used; script and subtitle download links disappear for simulation outputs.

Direct CLI (also available as `python -m app simulate`):

```bash
python -m app.simulation --duration 30 --quality draft --seed 42
python -m app.simulation --duration 180 --aspect-ratio 9:16 --quality standard
python -m app.simulation --duration 30 --fps 24 --segment-seconds 10 --quality draft --seed 149
python -m app.simulation --project-id sim_example --resume
python -m app.simulation --smoke --seed 42 --keep-scenes
```

Pass `--blender-path /your/path/to/blender` when the executable is not configured. `--smoke` renders a six-second obstacle sequence as two three-second draft segments. `--keep-scenes` retains original render frames and Blender scenes for inspection. Reusing a project ID always uses its persisted configuration/scenario; start a new project to change the seed or quality.

## API and jobs

POST the existing endpoint:

```json
{
  "video_type": "simulation_video",
  "simulation_type": "vehicle_obstacle",
  "duration": 60,
  "aspect_ratio": "16:9",
  "quality": "standard",
  "vehicle": "brick_basic_car",
  "theme": "colorful_toy_world",
  "difficulty": 2,
  "color": "random",
  "music": true,
  "sound_effects": true,
  "engine_sound": true,
  "seed": 847291
}
```

`POST /api/generate` persists initial project state, schedules existing FastAPI BackgroundTasks and returns the project ID without waiting for Blender. Poll `/api/progress/{id}` for `progress_percentage`, `progress_message`, `segments_progress`, attempts and checkpoint state. `POST /api/resume/{id}` resumes unfinished segments; `POST /api/regenerate/{id}/{segment_id}` invalidates just that segment. Requests for an already-running project return 409. Existing short-content requests without `video_type` remain compatible; uppercase `SHORT_CONTENT` / `SIMULATION_VIDEO` are accepted too.

Download `/media/{id}/artifact/final.mp4`, `scenario.json`, `metadata.json` or `thumbnail.png`. `/media/{id}/video` streams the same export.

The job runner is the repository's **in-process** task mechanism. OS-backed project leases prevent CLI and web workers from owning the same project simultaneously and release automatically when a worker exits. Progress detects ownership across processes, and regeneration holds the lease while updating state. Use one Uvicorn worker; a multi-worker setup still needs an external broker and a cross-process render limiter. A crash/restart preserves segment files/state but does not automatically enqueue work: resume using the UI button or endpoint. Parallelism is available across projects up to each process's render limit; segments within a project render sequentially. Generation is not a durable distributed queue.

Each render attempt writes to a unique private directory, so an orphan Blender child from a hard-killed worker cannot overwrite a resumed attempt's frames. Graceful cancellation kills/waits for Blender; a hard kill may leave its child running until rendering finishes. Stop or wait for that orphan to reclaim GPU resources before starting more jobs. The project's completed segments remain reusable.

## Architecture and render pipeline

```text
GenerateRequest → SimulationConfig → ScenarioGenerator
    → validated global track + events + SegmentPlan/WorldState
    → BlenderRenderer → blender_scene.py → obstacle plugins / vehicle / camera
    → PNG frames → checked FFmpeg H.264 segment
    → procedural WAV → VideoComposer.concat + AAC
    → full FFmpeg decode validation → existing export/download
```

Scenario JSON is persisted before rendering. Integer frame counts partition the exact duration into at most 30-second scenes, with a shorter final segment when necessary. Obstacles are selected using a local seeded RNG, no consecutive duplicates and at most two appearances in the preceding eight-section window. Parameters, colors and difficulty vary; moving mechanisms receive increased selection weight as difficulty progresses. The first obstacle begins about 1.7 seconds after motion starts. Track validation checks spawn clearance, section bounds/overlap, width, supported geometry and gap limits. It validates the planned animation course, not arbitrary physically simulated reachability.

WorldState includes the same car preset/color/damage, environment, track, lighting, camera style, difficulty/progress, global position, pitch, wheel angle and time. Each segment's end state is the next one's start state. Shared nearby obstacle context and decorations at global coordinates appear consistently across cuts. A new segment samples the next global frame, so the boundary is a continuous motion step rather than a duplicated frozen frame. Global camera and moving-obstacle time also continue.

Render processes receive JSON rather than command interpolation, capture combined stdout/stderr in per-segment logs, use `--python-exit-code 1`, and are killed on timeout/cancellation. Failed/invalid segments alone are rerendered; valid completed segments are fully decoded before reuse. Outputs are validated before being marked complete. Draft: 480×270 (or 270×480), 8 samples; standard: 1280×720, 32 samples; high: 1920×1080, 64 Eevee samples / 96 Cycles samples. All use 30 fps by default.

Audio generation works in one-second chunks with global event timestamps: mechanical movement, wheel ticks, ramp landing and a final success cue. Turning all audio options off produces a silent audio track. FFmpeg concatenates matching H.264 streams without re-rendering video, adds AAC, and sets faststart. There are no subtitle filters, text objects or fade-in intro.

## Storage, logging and resume

```text
outputs/projects/{id}/
  project.json
  scenario.json
  segments/001/
    scenario.json       # renderer payload: scenario + segment + resolution
    scene.blend         # latest successful scene; retained with --keep-scenes
    attempts/{attempt_id}/
      scenario.json
      scene.blend       # retained on failure / --keep-scenes
      frames/000001.png # private attempt output
      blender.log       # full stdout/stderr, including failed attempts
      ffmpeg.log
    preview.png
    blender.log         # full stdout/stderr
    ffmpeg.log
    timing.json
    output.mp4
  audio/simulation.wav
  logs/simulation.jsonl
  final/video.mp4
  final/composition.log
outputs/{id}/
  final.mp4
  scenario.json
  metadata.json
  thumbnail.png
```

JSONL logs include video/segment IDs, seeds, duration, obstacle list, attempt/retry count, elapsed render/composition time and error output. Segment `timing.json` separates Blender and FFmpeg execution time. PNGs and .blend files are cleaned only after completed export; locked temporary files produce a `cleanup_deferred` log rather than invalidating a completed MP4. MP4 segments, scene JSON, previews and logs remain available for resume/debugging.

The seed reproduces planning and deterministic animation. Bit-identical pixels/audio encodes are not guaranteed across different Blender versions, render engines, drivers or FFmpeg versions. Pin those versions and hardware for pixel-level reproducibility.

## Add an obstacle or vehicle

Subclass `BaseObstacle` in a separate module under `app/simulation/obstacles/`. Implement `createGeometry`, optionally override `configurePhysics`/`configureAnimation`, and implement a safe `height_at(x,time)` profile if the vehicle changes elevation. The shared interface also exposes entry/exit points, `validate` and `cleanup`. Register the type in `OBSTACLES`; the scene renderer requires no edits. Start/end profiles must return to the runway and width/gaps must fit the car. Use global time when keyframing animated objects so segment seams match. Keep bpy imports inside Blender-only methods. Add planning tests and extend `tests/render_smoke.py` coverage before enabling it in requests/UI.

Add vehicle parameters/geometry to `VehicleGenerator.PRESETS` and `create`, keep the same root transform/wheel animation contract, then extend SimulationConfig's allowed vehicle values and the dashboard. The MVP only enables the tested car; no unimplemented presets are advertised.

## Tests and debugging

```bash
python -m unittest discover -s tests -v
python -m compileall -q app tests
python -m app.simulation --smoke --seed 42 --keep-scenes
python tests/render_smoke.py --blender-path /your/path/to/blender
python tests/dashboard_smoke.py http://127.0.0.1:7860
```

Application tests cover scenario/track selection, seeds, segment counts and continuity, request validation and legacy defaults/dispatch, persisted retry/resume, subprocess errors/timeouts, audio-disabled behavior, corrupt caches and real FFmpeg concatenation. They do not require Blender or API keys. Real Blender render and browser checks are opt-in and separate; browser checks need Python Playwright and its Chromium browser. The repository had no pre-existing automated suite; added legacy tests cover the dispatch/storage contracts, not a paid/networked end-to-end short video run.

For browser checks: `pip install playwright` then `python -m playwright install chromium`. The HTTP test uses httpx, which is also installed by the existing OpenAI dependency. State files use same-directory atomic replacement; a failed replacement preserves the previous project JSON. Audio cancellation waits for the background WAV writer to close before allowing a resume to acquire project ownership.

Common failures:

- **Executable not found:** configure `BLENDER_PATH`; verify `blender --version` in the service environment.
- **Eevee/OpenGL context unavailable:** install supported graphics drivers or use `BLENDER_RENDER_ENGINE=CYCLES` for CPU rendering. See `blender.log`.
- **Unknown render engine:** use Blender 4.5 LTS with `BLENDER_EEVEE_NEXT`; engine identifiers differ between major versions.
- **Python traceback / incomplete frames:** full traceback is in the segment's `blender.log`. Scene scripts import bpy through Blender, not system Python.
- **Timeout:** reduce quality or increase `BLENDER_TIMEOUT`; resume the project. The process is killed and failure recorded.
- **FFmpeg codec errors:** verify H.264/AAC encoder availability in the binary selected by the existing discovery function. Logs retain encoder errors.
- **Invalid cached MP4:** decode validation invalidates the affected segment and rerenders it.
- **Disk space:** PNG sequences consume substantially more space than MP4; monitor the work volume. Keep cleanup enabled for production.
- **Interrupted app:** use resume; work is not automatically recovered by a broker.

## Docker considerations

The repository has no Docker deployment files. For a future image, install Blender and required system graphics libraries, mount `/data` persistently, supply explicit portable storage paths, use a single app worker, and configure the render engine for the available device. GPU Eevee needs an appropriate headless graphics context/driver; CPU Cycles avoids relying on a GPU render device. Do not run the Blender installation command on every request or ship render state on an ephemeral filesystem.

## Next improvements

Validate full 3/5/10-minute workloads and segment seam screenshots on target hardware, then enable longer public presets. Add controlled crash/recovery motion, richer procedural worlds, recorded or synthesized foley variation, additional camera/vehicle presets, and obstacle-specific event timing. A durable queue with shared render limits and atomic cross-process project ownership is the next infrastructure step before multi-worker/distributed rendering.
