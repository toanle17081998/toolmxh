# Multi-content construction-brick simulation framework

## Intent and audit

The product is a procedural physical-experiment studio, not just a crawler on a random track. Content can ask a question, build a design, run trials, compare measured outcomes or refine a design after a failed attempt. Vehicle changes are intentional between trials; there is no morphing during a physical run.

Audit: the current director creates only the same drop/ramp/stairs/gap sequence (`app/simulation/director.py`). The factory has one fixed four-wheel model (`physics_vehicle.py`). The scene knows only a vehicle course (`physics_scene.py`); telemetry assumes successful progress and rejects ordinary failures. The service already provides jobs, leases, rendering, cache, audio, composition and exports. Those are reusable. Current Short Content/health work in the working tree is separate user work and must be preserved.

## Implementation plan

1. Add a registry/catalog with ideas, capabilities and explicit render readiness. Cover the agreed content families without disguising a catalog idea as a working simulator.
2. Add deterministic, seed/history-driven idea generation; structured experiment plans and parameterized vehicle designs. Preserve `obstacle_course` as the legacy request default. New `auto` requests choose among supported content handlers.
3. Add independent physical trial scenes: bridges, brick-wall impacts, drop tests, payloads, gravity-driven balls and domino chains. Measure results; expected failure is content, while non-finite/explosive/corrupt simulations are errors.
4. For comparisons, keep the challenge/environment fixed and vary the declared design/parameter. For improve/retry, derive the next candidate from the preceding measured outcome. Never assert a prewritten winner.
5. Reuse bounded render segments and per-trial authoritative telemetry/cache. Preserve continuity inside a trial; reset/assembly between trials is an intentional story boundary. Cache keys include trial/design/challenge and implementation/Blender version.
6. Add dashboard content selector, idea cards, number of trials and optional experiment labels; use existing project/progress/download mechanisms. Labels identify experiments and measured results, not narration subtitles.
7. Verify real clips showing different designs/physical interactions and regress the existing course and Short Content contracts. Document exactly which families are implemented and tested.

## Components

- `content.py`: registry and seeded ideas, no API keys or LLM dependency.
- `experiments.py`: design/experiment planning and outcome-driven refinement.
- `worlds/`: separate world plugins with common create/evaluate contract.
- `experiment_scene.py`: shared headless solve/validate/playback orchestration.
- Existing factory/renderer/service/model/API/UI: minimal integration, typed plans/results and cache identity.

## Content catalog

Obstacle course; build challenge; improve/retry; design comparison; controlled parameter test; destruction/impact; drop/landing test; bridge engineering; cargo/balance; time trial; limited materials; mechanical machines; chain reaction; marble run; ball race; survival; escalating limits.

Limited-materials and articulated mechanical machines need distinct verified builders and remain unavailable until implemented. A disabled catalog entry is not a rendering capability. Other families may share a physical world but have different designs, controlled variables, goals, outcome metrics and narrative structure.

## Verification requirements

- Same seed + same inputs/history produces the same ideas and designs.
- Unknown/unavailable types and incompatible ideas are rejected before enqueue.
- A comparison uses the same challenge for every candidate.
- Vehicle preset changes alter real chassis/wheel geometry, mass or motor parameters.
- Wall bricks, bridge members, balls and dominoes are real active/passive Bullet bodies.
- Ordinary falling/stuck/failed trials yield measured outcomes and bounded clips, not infinite retries.
- Results/audio are replaced on regeneration, not duplicated; resume keeps compatible trial plans.
- API catalog/ideas are inexpensive and never execute Blender.
- Existing Short Content and obstacle-course defaults remain compatible.

## Status

Implemented catalog: **17 families**, of which **15 have a renderer** (including the original obstacle course). `budget_build` and `mechanisms` remain disabled and are rejected by request validation. There are 51 curated idea templates; auto suggestions choose different families, honor recent idea history and are deterministic for seed + inputs/history. No LLM/API key is required.

### Active content behavior

- Comparisons: wide four-wheel, narrow four-wheel and six-wheel chassis on the same bridge.
- Improve/retry: a failed crossing narrows the axle/body and lowers the center of mass; a successful crossing tests a lighter candidate. An incomplete trial is not misrepresented as a design failure.
- Parameter tests: wheel radius, wheelbase or mass with the other design settings held constant.
- Impact: independently simulated wall bricks and real fixed-joint bumper colliders. Mounted bumper colliders are clear of wheel extents, not invisible wheel brakes.
- Drop tests: gravity, fall speed, body tilt and final landing orientation. The assembled vehicle is not destructible; this tests landing behavior, not individual brick durability.
- Bridge engineering: passive beam, breakable fixed-joint planks and reinforced joints; bridge members are measured physical bodies.
- Cargo: a payload rigid body attached to the chassis; load and placement affect the solved vehicle.
- Time trials: measured finish times; equal frame times are ties.
- Domino and gravity-ball worlds: independent active bodies, real contacts and measured chain completion/finish times. Equal-time ball finishes are reported as a tie group, never an arbitrary winner.
- Survival: declared goal matches the world evaluator; normal failures remain content.
- Limit tests: nondecreasing gap sizes (capped at the supported world bound) and the first observed failed limit in results.

Each content experiment lasts at most ten seconds. `trial_count` is a minimum; longer durations add bounded attempts rather than showing a stuck object for minutes. Segments can split an attempt without resetting it. Geometry is fixed during each test; assembly and different candidate designs are explicit between-test phases. Labels identify trial/design and measured result, and can be disabled; there is no TTS or narration subtitle track.

### API / dashboard / CLI

The dashboard now offers content type, seed-based idea cards, minimum trial count, quality/camera/audio and experiment labels. It also displays measured results after completion. Planned categories are visibly disabled. Short Content controls and mode restoration remain available.

```json
{
  "video_type": "physics_simulation_video",
  "simulation_type": "brick_physics_experiment",
  "content_type": "design_comparison",
  "idea_id": "design_comparison:0",
  "duration": 20,
  "trial_count": 3,
  "quality": "preview",
  "show_labels": true,
  "seed": 42
}
```

- `GET /api/simulation/catalog`: families and render readiness.
- `POST /api/simulation/ideas`: `{seed, content_type, count, history, include_planned}` → resolved seed and idea cards. Does not launch Blender.
- Existing generate/progress/resume/regenerate endpoints are reused.
- `experiment_results.json`, `scenario.json`, `metadata.json` and MP4 exports use the existing artifact/download route.
- Legacy requests default to `obstacle_course`. Legacy video-type aliases are accepted. New UI uses `brick_physics_experiment`; old simulation-type names remain compatible.

```powershell
python -m app.simulation --content-type design_comparison --idea-id design_comparison:0 --duration 20 --trials 3 --quality preview --seed 42
python -m app.simulation --content-type improve_retry --duration 20 --trials 3 --seed 42
python tests/simulation_content_smoke.py --all
python tests/render_content_examples.py --keep-scenes
python tests/verify_content_sample.py content_design_comparison_42 content_improve_retry_42 content_destruction_42 content_ball_race_42 content_chain_reaction_42
python -m unittest discover -s tests -v
```

### Actual evidence

**42 real Bullet trials across the 14 non-course renderable families** passed finite-transform/body-count/collider checks. Every non-drop vehicle trial also demonstrated real forward travel before its challenge. Examples: wide car fails while narrow/four-wheel and six-wheel cars succeed; an unreinforced plank bridge loses all eight members while the reinforced bridge holds; smaller gaps succeed and larger ones fail; domino chains complete; gravity balls race without scripted translation.

Five real preview MP4s were rendered, fully decoded and inspected via extracted frames:

| Sample | Duration / frames | Path |
|---|---|---|
| Three vehicle designs on one bridge | 20s / 600 | `outputs/content_design_comparison_42/final.mp4` |
| Measured failure → revised design → retry | 20s / 600 | `outputs/content_improve_retry_42/final.mp4` |
| Vehicle impacts independent brick blocks | 6s / 180 | `outputs/content_destruction_42/final.mp4` |
| Three gravity-driven balls | 6s / 180 | `outputs/content_ball_race_42/final.mp4` |
| Domino chain reaction | 6s / 180 | `outputs/content_chain_reaction_42/final.mp4` |

All are 480×270, 30fps, with original synthesized audio. `content_acceptance.json`, extracted `trial_*.png`, scene/attempt logs and measured result JSON are kept locally under ignored outputs. The six-second samples are developer smoke examples; public video creation starts at twenty seconds.

The complete **76-test suite passed**. Browser smoke passed catalog loading, disabled planned categories, idea selection, canonical payload, progress/resume and Short Content restoration. A real FFmpeg Short Content composition test also verified video/audio/dimensions, preserved an old master on render failure and rejected corrupt media. Paid/networked health/Short Content generation was not rerun.

### Review / integrity corrections included

Accepted health plans are cached by narration/context/character definitions; targeted regeneration preserves the saved script and unmodified actual-video review. Generation fingerprints ignore review prose but include timeline duration and dimensions. AUTO health routing distinguishes common technology metaphors from anatomical topics. Shared Short Content composition uses checked subprocesses, unique temporary output, real decode QC and an atomic swap before export; stale existing MP4s cannot create false completion. Windows state writes retry bounded native sharing/access errors without truncating the old JSON.

### Remaining scope

No long-form readiness claim follows from catalog size. Full 5–30-minute videos and all seeds/aspects/cameras are not visually validated. Shapes/materials/worlds are intentionally simple; suspension/steering, individual vehicle-brick breakage, exact material budgets, articulated cranes/machines, distributed render queues and restoring Bullet velocities at an arbitrary checkpoint remain future work. The legacy continuous obstacle course still uses its whole-trajectory cache; the new experiment content uses bounded per-attempt scenes. Comparison horizons can differ by one frame when the requested duration cannot divide evenly; frame-resolution ties are preserved.
