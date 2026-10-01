# Simulation Video Implementation Plan

> Superseded by [PHYSICS_SIMULATION_REFACTOR_PLAN.md](PHYSICS_SIMULATION_REFACTOR_PLAN.md); preserved as the audit record of the prior animated traversal design.

> Execution: implement in this session, in the existing checkout. The user's supplied specification authorizes the complete MVP after this plan is written. Preserve the existing short-content pipeline.

**Goal:** Produce real, downloadable Blender-rendered toy obstacle videos without narration, subtitles, or AI service dependencies.

**Architecture:** Add a separate SimulationVideoService selected before constructing VietnameseVideoFactory. Plan deterministic, frame-bounded segments with explicit WorldState, render each through a headless BlenderRenderer, synthesize event audio, and compose through VideoComposer. Keep original short requests and stored projects backward compatible.

**Tech stack:** Python 3.10+, Pydantic v2, FastAPI BackgroundTasks, plain HTML/JavaScript, Blender 4.5 LTS, FFmpeg, NumPy; unittest for application tests.

**Spec:** User-supplied “Add Long-form Visual Simulation / Satisfying Video Mode” request, sections 1–29. This document records the repository-specific decisions.

## Repository analysis and reuse

| Component | Current behavior | Simulation reuse |
| --- | --- | --- |
| `app/web/server.py` | FastAPI generate endpoint, in-process background tasks, polling, regeneration, media downloads | Mode dispatch, persistent initial state before enqueue, shared polling and media routes, simulation resume/retry |
| `app/factory.py` | Topic → LLM → TTS → measured timeline → image/video providers → audio → ASS subtitles → composition | Preserve unchanged; default SHORT_CONTENT; no simulation calls to its providers |
| `app/models/project.py` | Pydantic project config/state and scene progress | Add mode/config, simulation stages and segment state with backward-compatible defaults |
| `app/core/state_manager.py` | Atomic filesystem JSON; scene directories and resume | Use same project manager and project.json; segments live under the project |
| `app/engines/composer.py` | FFmpeg discovery and concat/encode with subtitles/fades | Add independent segment composition method with checked subprocess errors, stream-copy video and no intro fade |
| `app/config.py` | .env-backed Settings, workspace/storage paths, FFmpeg PATH/imageio fallback | Add Blender configuration with portable path discovery |
| `app/web/templates/index.html` | Tailwind CDN dashboard, controls, polling, scene cards, preview/download | Add mode selector and simulation controls; reuse tracker/cards/preview |
| CLI / `app/__main__.py` | argparse commands | Separate simulate command with resume and smoke options |
| QC | ffprobe where available, size-based fallback | New strict simulation media validation using FFmpeg decoding/metadata, without weakening short behavior |

There is no database, external broker, Dockerfile/Compose, package frontend, or existing test directory. Projects are the database. The existing job system is in-process BackgroundTasks, so resume after process restart is explicit, not an automatically recovered durable queue. No infrastructure replacement is warranted for MVP. Provider families and existing engine/model/core interfaces were inspected; their short-content behavior stays separate.

## Global constraints and scope

- MVP: `brick_basic_car`; ramp, rotating_bar, stairs, hammer, moving_platform; `colorful_toy_world`; `dynamic_follow`.
- Public duration 30–180 seconds, including 30/60/180 presets and custom; 9:16 or 16:9. Keep 5/10 minute and 1:1 controls disabled until longer renders are validated. Internal planner supports up to 1800 seconds.
- Deterministic animation is the reliable source of vehicle motion; passive/kinematic rigid bodies supply collisions and gravity infrastructure. Full suspension/driving and uncontrolled crashes are deferred. Obstacle height profiles and safe timing make the path traversable.
- Segments are at most 30 seconds, planned on integer frame counts. Global track coordinates/time, appearance, camera parameters, progress and cosmetic damage pass through WorldState. Shared section context at boundaries avoids scene discontinuities.
- Original geometry/materials and procedural audio only. No branded assets or external audio downloads.
- Blender processes are bounded per server process by `BLENDER_MAX_PARALLEL_JOBS`, timed out and killed on cancellation. Segment progress and attempt counts persist; retry only failed/invalid segments. No Blender work in the request handler.

## Review focus

1. Legacy requests/projects lacking video_type continue as short_content and call the original factory.
2. Bad config, missing Blender, stale/corrupt cached videos and worker cancellation never become false completion.
3. Partial final segments and boundary poses preserve exact frame duration and continuity.
4. Concurrent/repeated retry requests cannot race on one project's JSON; different projects share the render limit.
5. Audio-disabled runs still export valid MP4; source frames and Blender stderr remain available on failure.

## File map and tasks

### Task 1: deterministic planning and schemas

Create `app/simulation/{__init__,models,scenario,track,selection}.py` and `app/simulation/obstacles/{__init__,base,ramp,stairs,rotating_bar,hammer,moving_platform}.py`.

Interfaces: SimulationConfig → ScenarioGenerator.generate(config) → Scenario with SegmentPlan and WorldState; SimulationTrackGenerator.generate(duration,difficulty,theme,seed) → validated sections. validateTrack rejects overlaps, boundaries, blocked spawn and unreachable gaps. Obstacle plugins share geometry/physics/animation/entry/exit/validate/cleanup and motion profile methods, importing bpy only inside render-time helpers.

- [ ] Write and run failing ScenarioGeneratorTest, TrackGeneratorTest, ObstacleSelectionTest, SeedReproducibilityTest and SegmentPlannerTest in `tests/test_simulation_planning.py`.
- [ ] Implement stable seeds, anti-repeat window, difficulty progression, randomized parameters, timed events, checkpoints, segment context, state passing and frame-aligned duration.
- [ ] Run `python -m unittest discover -s tests -v`; planning tests pass.

### Task 2: real Blender renderer and composition

Create `app/simulation/{blender_renderer,blender_scene,geometry,vehicle,camera,audio,media}.py`; extend config/composer. BlenderRenderer.render_segment receives a serialized scenario+segment and writes PNG frames, scene.blend and output.mp4. SimulationAudioManager generates WAV in small chunks from shared event time. Blender imports no application dependencies beyond standard Python.

- [ ] Add renderer failure/timeout/concurrency and composition tests in `tests/test_simulation_pipeline.py`; run before implementation.
- [ ] Build colorful beveled brick geometry, animated wheels, five plugin obstacles, stable follow camera and studio lights; draft/standard/high resolutions and samples.
- [ ] Render headlessly to PNG, encode checked H.264 segments using existing FFmpeg binary discovery, then concatenate and add procedural WAV through VideoComposer.
- [ ] Run short real render smoke test and validate decoded frame count, dimensions, sound, no subtitles and nonempty scenes. Keep smoke assets under ignored outputs.

### Task 3: persisted jobs, API and frontend

Create `app/simulation/service.py` and smoke/CLI entry point; extend `app/models/project.py`, `app/web/server.py`, `app/cli.py` and existing dashboard.

Interfaces: SimulationVideoService.generate_video(project_id, config) returns existing final_video_path result shape. Existing /api/generate accepts optional video_type and flat simulation controls; short default retained. /api/resume/{project_id} resumes simulation; /api/regenerate handles segment invalidation for simulations. Persist resolved seed and scenario before rendering, state after each attempt, and checked final metadata/output.

- [ ] Add SimulationVideoRequestTest, legacy dispatch, resume/retry/download tests; prove request returns before rendering and API rejects unsupported MVP choices.
- [ ] Implement shared-job dispatch, no duplicate jobs per project, progressive segment status and explicit resume.
- [ ] Add mode selector, simulation controls and mode-specific progress labels/downloads; hide short settings for simulations; preserve short inputs.
- [ ] Run full application tests and check dashboard script syntax and mode switching.

### Task 4: operations documentation and final validation

Create `docs/SIMULATION_VIDEO.md`, update README/.env.example and requirements where existing web dependencies are missing.

- [ ] Document installation, environment variables, local/API/CLI use, schema, plugins, presets, retry, Docker/headless display considerations and real MVP limitations.
- [ ] Run full test discovery (including short regression tests), Python compilation, real multi-segment smoke MP4, inspect logs and frames; fix observed faults.
- [ ] Review diff and report changed files, commands, variables, evidence and limitations. No implicit deployment or commit.
