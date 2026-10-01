# Health visual refactor

## Audit and root causes

- Script segmentation: `app/models/script.py` stores narration per SceneScript;
  `app/engines/timeline.py:31–65` preserves scene IDs and lets TTS determine duration.
- Visual planning: `app/factory.py:160–170` calls a generic storyboard LLM.
  `app/providers/llm/gemini.py:151–179` prioritizes a mascot in every scene,
  a generic medical laboratory, pointing, blinking and camera motion, not the
  current biological mechanism. OpenAI has only a generic storyboard instruction.
- Health logic: `app/models/health_organs.py:262–282` uses substring detection,
  conflates blood with heart and drinking with kidneys, and defaults to liver.
  Existing definitions have irrelevant permanent props (brooms, water glasses)
  and occasionally obscure recognizable anatomy (cloud lungs, bean stomach).
- Image generation: Gemini, DALL-E and Fal wrap prompts in photorealistic styles.
  Real media search accepts the first search result without semantic validation.
  Earlier fixes removed unrelated cosmos/server/procedural fallbacks, but organ
  keywords alone still permit generic medical images.
- Video generation: Wan and Veo silently downgrade to still-image camera motion.
  No prompt or pixel relevance assessment, shared organ references, or health debug
  records currently exist. `factory.py` enumerates timeline indices rather than
  scene IDs and references a nonexistent SceneTiming.narration in its fallback.

## Dedicated mode

`visual_mode`: AUTO (default), HEALTH_CHARACTER, STANDARD (explicit opt-out).
High-confidence bounded health/anatomy terms activate the mode. Detection is only
dispatch; it never substitutes for semantic narration analysis. Simulation stays
on its existing separate pipeline.
Automatic routing uses the topic and script title, not incidental narrator names
inside dialogue. Common non-health phrases (blood moon, eye of the storm,
computer sleep mode) do not activate organ characters.

## Files and responsibilities

- `app/health/models.py`: typed semantic analysis, scene micro-story, character
  definitions/bible, score components, and prompt planning results.
- `app/health/registry.py`: eleven recognizable organ characters, consistent
  proportions, face placement, limbs, colors, animation, and body environments.
- `app/health/planner.py`: HealthVisualAnalyzer calls the real LLM on complete
  narration/context; independent relevance evaluation compares narration and
  actual image/video prompts. Rejected plans are regenerated, bounded to three
  attempts. Unknown processes use a direct organ visualization and preserve
  uncertainty, never invented mechanisms or unrelated B-roll.
- `app/health/generation.py`: generate/store reference images before scenes;
  prefer reference-conditioned generation, keep prompts and deterministic seeds
  when provider lacks references; prohibit stock/procedural generic fallback.
  Require actual animated video providers, not still-image camera engines.
- `app/providers/llm/{base,gemini,openai}.py`: reusable typed-JSON completion for
  semantic analysis and independent relevance evaluation.
- `app/providers/image/{base,gemini_imagen,dalle,real_media}.py`: explicit health
  image methods, native animation styling, and reference capability reporting.
- `app/providers/video/{base,veo,wan}.py`: strict health animation paths propagate
  provider failures instead of silently returning stills.
- `app/factory.py`, `app/models/project.py`, `app/web/server.py`, `app/cli.py`:
  mode routing, persistence, scene-ID correct lookup, health debug and overrides.
- `tests/test_health_visuals.py`, `app/health/quality.py`: liver/alcohol,
  kidney filtration and stomach digestion fixtures, rejection tests, provider
  boundary checks, continuity, multi-organ and non-health regression checks.

## Semantic analysis and prompt strategy

Analyze subject(s), process, state, cause, consequence, emotional response,
required objects, narration-explicit people/props, environment, uncertainty,
and SETUP → ACTION → REACTION before writing any scene visual prompt.
Organ definitions are reused verbatim, with anatomy taking priority over face
and limbs. Every video prompt has subject, environment and camera movement.
Metaphors are explicitly identified as explanatory representations, not literal
biology. Preserve qualifiers such as can/may; no instantaneous disease or cure.

## Relevance and fallback

Independent evaluator awards subject 0–30, process 0–30, cause/effect 0–20,
action 0–10 and clarity 0–10. Total <80 rejects the plan. Missing character,
inconsistent IDs, forbidden unrelated generic visuals and missing movement are
hard failures regardless of aesthetic score. Evaluation uses narration, analysis,
both prompts and the bible, not just matching keywords. Failed attempts are saved.
If a process cannot be established, show the known organ responding to context
without speculative causality. If no anatomical subject can be established,
request a corrected analysis or stop with a useful error; never choose a doctor.

Generate references at `character_reference/<organ>.png`; store
`health_character_bible.json` and `health_debug/scene_NNN.json` (narration,
analysis, organ/process, image/video/final prompt, score breakdown, attempts,
provider and reference paths). The prompt gate is not proof of pixel correctness:
an actual video still requires frame/motion inspection.

Reference/scene image inspection compares generated pixels with the character
bible and reference images. Video inspection uses three chronological frame
samples and reference designs. This cannot prove every motion between sampled
frames; human final-video inspection remains part of live acceptance.

## Verification

Run liver/alcohol (healthy → incoming substances → processing → workload →
stress), kidney (blood → waste separation → cleaned blood), stomach (food →
controlled acid + mixing → breakdown) quality fixtures. Also test negation,
uncertainty, multiple organs, generic exceptions explicitly mentioned in narration,
manual override, low relevance rejection, stable references and non-health routing.
`python -m app.health.quality` performs live semantic planning and image/video
generation; logs/artifacts include exact provider failures if credentials, network,
quota or model availability block an actual render. Never report a motion-only
still preview as a successful biological animation.

## Recorded verification (2026-10-01)

- `python -m unittest discover -s tests -p "test_*.py"`: **58 tests passed**.
  `git diff --check` on the changed health/integration files passed.
- Automated quality and regression tests cover all three scripts, stable character
  anchors, micro-story movement, multiple organs, uncertain-process fallback,
  mandatory generic exclusions, rejection/regeneration, reference reuse, rejection
  of unrelated generated images, strict Wan/Veo failures, and valid Veo durations.
- Real LLM semantic planning succeeded using `gemini-2.5-flash-lite`:
  liver five scenes 98–100 on the first successful all-case run; kidney three
  scenes 97–100; stomach three scenes 100. A later liver render attempt re-planned
  successfully at 95–100. Prompts/debug artifacts were inspected: liver uses
  alcohol/metabolic products/fat buildup; kidneys use filtration/reabsorption and
  blood/urine separation; stomach uses gastric secretion and mixing. No generic
  doctor/hospital/restaurant B-roll is planned.
- Live evaluation initially misread organ faces as costumes; clarified that faces
  ON recognizable organs are required, while humans IN costumes are rejected.
  Kept the threshold at 80. Bare-array JSON response parsing was corrected using
  a health-specific structured response schema rather than the generic brace
  extractor, which strips array containers.
- Actual liver generation was attempted. It reached character-reference
  generation, then Gemini image returned `429 RESOURCE_EXHAUSTED`, free-tier image
  quota **0**. A reference-capable alternative image model was also attempted and
  blocked. OpenAI live planning encountered RateLimitError. No final health video
  was generated; image continuity, biological motion and final visual acceptance
  are not yet verified against actual AI output.
- Artifacts: `outputs/health_quality/{liver,kidney,stomach}/`; each has narration,
  storyboard, bible, per-scene decisions and `quality_report.json`.

Resume actual generation after enabling working image/video quota:

```bash
python -m app.health.quality --case liver --reuse-plan --llm-model gemini-2.5-flash-lite --image-model gemini-3.1-flash-image
```

The command accepts `--image-model` and `--video-model` overrides. `--reuse-plan`
requires identical narration and accepted saved scores; it does not accept a
rejected plan merely to get a render. Live image/video failures remain explicit.
