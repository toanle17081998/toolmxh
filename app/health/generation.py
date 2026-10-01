import asyncio
import hashlib
import json
import os
from pathlib import Path

from PIL import Image
from pydantic import BaseModel

from app.config import get_ffmpeg_binary, settings
from app.health.models import RelevanceScore
from app.health.planner import save_json
from app.providers.image.dalle import OpenAIDalle3Provider
from app.providers.image.gemini_imagen import GeminiImagenProvider
from app.providers.video.veo import GoogleVeoVideoProvider


class CharacterReview(BaseModel):
    recognizable_organ: bool
    organ_is_character: bool
    consistent_design: bool
    relevant_setup: bool
    explanation: str

    @property
    def accepted(self):
        return all((self.recognizable_organ, self.organ_is_character,
                    self.consistent_design, self.relevant_setup))


class HealthVisualGenerator:
    """Strict health generation: no stock and no camera-over-still substitution."""

    def __init__(self, llm, image_provider, video_provider, image_model="auto"):
        self.llm = llm
        self.image_provider = image_provider
        self.video_provider = video_provider
        # Auto uses a reference-conditioned image model where available.
        gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        if image_model.lower() in ("auto", "real_media"):
            if gemini_key:
                self.image_provider = GeminiImagenProvider(api_key=gemini_key)
            elif openai_key:
                self.image_provider = OpenAIDalle3Provider(api_key=openai_key)
        if (type(video_provider).__name__ == "WanVideoProvider"
                and not video_provider.fal_key and not video_provider.replicate_token and gemini_key):
            self.video_provider = GoogleVeoVideoProvider(api_key=gemini_key)

    def preflight(self):
        if not self.image_provider.supports_health_characters:
            raise RuntimeError(f"{type(self.image_provider).__name__} has no strict health-character image path")
        if not self.video_provider.supports_health_animation:
            raise RuntimeError("HEALTH_CHARACTER requires actual biological animation (Veo or Wan API); camera-only engines are not sufficient")
        if (type(self.video_provider).__name__ == "WanVideoProvider"
                and not self.video_provider.fal_key and not self.video_provider.replicate_token):
            raise RuntimeError("HEALTH_CHARACTER Wan animation requires FAL_KEY or REPLICATE_API_TOKEN")

    async def _review_image(self, image_path, characters, setup="neutral character reference", reference_paths=None):
        prompt = (
            "Inspect the actual FIRST image, not the text prompt. Does it show the specified recognizable "
            "anatomical organ(s), with an expressive face on the organ itself (not a person/costume)? "
            "Is it a polished 3D educational character with unobscured anatomy? Does it represent the setup? "
            "Compare shape, face placement, color, proportions with subsequent reference images if present. "
            "No unrelated human/doctor/hospital/food scene. Return JSON matching schema:\n"
            + json.dumps(CharacterReview.model_json_schema())
            + "\nCHARACTERS: " + json.dumps(characters, ensure_ascii=False)
            + "\nSETUP: " + setup
        )
        return CharacterReview.model_validate(await self.llm.complete_json(
            prompt, image_paths=[str(image_path), *[str(path) for path in reference_paths or []]],
            schema=CharacterReview.model_json_schema(),
        ))

    @staticmethod
    def _normalize_image(path, width, height):
        with Image.open(path) as source:
            source.convert("RGB").resize((width, height), Image.Resampling.LANCZOS).save(path, "PNG")

    async def generate_references(self, bible, project_dir, width, height):
        self.preflight()
        directory = project_dir / "character_reference"
        directory.mkdir(parents=True, exist_ok=True)
        for organ, character in bible.characters.items():
            path = directory / f"{organ}.png"
            definition = character.model_dump(exclude={"reference_image"})
            fingerprint = hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest()
            manifest_path = directory / f"{organ}.json"
            if path.exists() and manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("fingerprint") == fingerprint and manifest.get("accepted"):
                    character.reference_image = str(path)
                    continue
            prompt = (
                character.anchor() + "\nSingle neutral character design reference, front three-quarter view, "
                "entire recognizable organ visible against a clean soft neutral background. Friendly focused "
                "expression, no disease, no props, no text or labels. " + character.negative_constraints
            )
            feedback = ""
            for attempt in range(2):
                await self.image_provider.generate_health_image(prompt + feedback, str(path), width, height, character.seed)
                self._normalize_image(path, width, height)
                review = await self._review_image(path, [definition])
                save_json(manifest_path, {"fingerprint": fingerprint, "definition": definition,
                                         "prompt": prompt + feedback, "attempt": attempt + 1,
                                         "provider": type(self.image_provider).__name__,
                                         "accepted": review.accepted, "review": review.model_dump()})
                if review.accepted:
                    break
                feedback = "\nCorrect this image review failure: " + review.explanation
            if not review.accepted:
                raise RuntimeError(f"Health character reference rejected for {organ}: {review.explanation}")
            character.reference_image = str(path)
        save_json(project_dir / "health_character_bible.json", bible.model_dump())

    @staticmethod
    def fingerprint(narration, plan, bible, duration=None, width=None, height=None):
        organs = [plan.analysis.primary_subject, *plan.analysis.secondary_subjects]
        data = {"narration": narration, "plan": plan.model_dump(exclude={'relevance'}),
                "characters": {organ: bible.characters[organ].model_dump() for organ in organs},
                'duration':duration,'width':width,'height':height}
        digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode())
        for organ in organs:
            digest.update(Path(bible.characters[organ].reference_image).read_bytes())
        return digest.hexdigest()

    async def generate_scene(self, narration, plan, bible, scene_dir, project_dir, duration, width, height):
        scene_id = plan.analysis.scene_id
        debug_path = project_dir / "health_debug" / f"scene_{scene_id:03d}.json"
        debug = json.loads(debug_path.read_text(encoding="utf-8")) if debug_path.exists() else {'narration':narration,'semantic_analysis':plan.analysis.model_dump()}
        organs = list(dict.fromkeys([plan.analysis.primary_subject, *plan.analysis.secondary_subjects]))
        references = [bible.characters[organ].reference_image for organ in organs]
        characters = [bible.characters[organ].model_dump() for organ in organs]
        image = scene_dir / "reference.png"
        video = scene_dir / "video.mp4"
        seed = bible.characters[plan.analysis.primary_subject].seed
        debug.update({"character_references": references,
                      "reference_conditioned": self.image_provider.supports_reference_images,
                      "image_provider": type(self.image_provider).__name__,
                      "video_provider": type(self.video_provider).__name__, "duration": duration})
        save_json(debug_path, debug)
        feedback = ""
        for attempt in range(2):
            final_image_prompt = plan.image_prompt + feedback
            await self.image_provider.generate_health_image(
                final_image_prompt, str(image), width, height, seed,
                reference_images=references if self.image_provider.supports_reference_images else None,
            )
            self._normalize_image(image, width, height)
            image_review = await self._review_image(image, characters, plan.analysis.micro_story.setup, references)
            debug.update({"final_image_prompt": final_image_prompt, "image_review": image_review.model_dump()})
            save_json(debug_path, debug)
            if image_review.accepted:
                break
            feedback = "\nCorrect the image review failure: " + image_review.explanation
        if not image_review.accepted:
            raise RuntimeError(f"Health scene {scene_id} image is unrelated/inconsistent: {image_review.explanation}")
        feedback = ""
        for attempt in range(2):
            final_video_prompt = plan.video_prompt + feedback
            debug["final_generation_prompt"] = final_video_prompt
            save_json(debug_path, debug)
            try:
                await self.video_provider.generate_health_video(
                    image_path=str(image), prompt=final_video_prompt, output_path=str(video),
                    duration_seconds=duration, width=width, height=height, seed=seed,
                )
                await self._normalize_video(video, duration, width, height)
                frames = await self.extract_frames(video, scene_dir / "health_inspection", duration)
                review_prompt = (
                    "Evaluate the ACTUAL chronological video frames against this exact narration. "
                    "Ignore how attractive they are. Primary subject /30, biological process /30, "
                    "cause+effect /20, action /10, clarity /10. Look for visible setup-action-reaction: "
                    "incoming substances, processing, and consequences where narrated. A still organ "
                    "with only camera motion does not demonstrate a narrated biological action. "
                    "Reject generic B-roll, wrong organs, unsupported claims and inconsistent character "
                    "design. Frame samples are evidence of visible stages, not proof of every frame. "
                    "HEALTH_CHARACTER intentionally requires eyes, mouths and small arms ON recognizable "
                    "organs. These are allowed educational metaphors, not organ costumes. Never deduct "
                    "points for required organ-character features; reject a human in a costume instead. "
                    "The last images are character references for continuity. Return JSON schema:\n"
                    + json.dumps(RelevanceScore.model_json_schema())
                    + "\nNarration: " + narration
                    + "\nExpected semantic analysis: " + plan.analysis.model_dump_json()
                )
                review = RelevanceScore.model_validate(await self.llm.complete_json(
                    review_prompt, image_paths=[str(path) for path in frames] + references,
                    schema=RelevanceScore.model_json_schema(),
                ))
                debug.update({"video_attempt": attempt + 1, "frame_paths": [str(path) for path in frames],
                              "actual_visual_review": review.model_dump(), "actual_visual_score": review.total,
                              "actual_visual_accepted": review.accepted})
                save_json(debug_path, debug)
                if review.accepted:
                    return str(video)
                feedback = "\nCorrect the actual video review failure: " + review.explanation
            except Exception as error:
                debug.update({"generation_error": type(error).__name__ + ": " + str(error),
                              "actual_visual_accepted": False})
                save_json(debug_path, debug)
                raise
        raise RuntimeError(f"Health scene {scene_id} animation rejected: {review.explanation}")

    @staticmethod
    async def _run_ffmpeg(arguments):
        process = await asyncio.create_subprocess_exec(get_ffmpeg_binary(), "-y", *arguments,
                                                       stdout=asyncio.subprocess.DEVNULL,
                                                       stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        if process.returncode:
            raise RuntimeError("Health video FFmpeg failed: " + stderr.decode("utf-8", errors="replace")[-1500:])

    @classmethod
    async def _normalize_video(cls, path, duration, width, height):
        normalized = path.with_name("health_normalized.mp4")
        await cls._run_ffmpeg(["-stream_loop", "-1", "-i", str(path), "-t", str(duration),
                              "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30",
                              "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(normalized)])
        normalized.replace(path)

    @classmethod
    async def extract_frames(cls, video, directory, duration):
        directory.mkdir(parents=True, exist_ok=True)
        frames = []
        for index, fraction in enumerate((0.05, 0.5, 0.9)):
            path = directory / f"frame_{index}.png"
            await cls._run_ffmpeg(["-ss", str(duration * fraction), "-i", str(video),
                                  "-frames:v", "1", str(path)])
            if not path.exists():
                raise RuntimeError("Health animation produced no inspectable video frame")
            frames.append(path)
        return frames
