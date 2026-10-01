import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.health.generation import CharacterReview, HealthVisualGenerator
from app.health.models import HealthScenePlan, HealthSemanticAnalysis, RelevanceScore, VisualMode
from app.health.planner import HealthVisualAnalyzer, HealthVisualPlanner, build_health_prompts, save_json
from app.health.quality import quality_script
from app.health.registry import HealthCharacterRegistry, detected_organs, resolve_visual_mode
from app.models.project import ProjectConfig
from app.models.script import SceneScript, StructuredScript
from app.providers.image.gemini_imagen import GeminiImagenProvider
from app.providers.image.real_media import RealVisualMediaEngine
from app.providers.llm.offline import OfflineBrainProvider
from app.providers.video.semantic_engine import SemanticMotionVideoEngine
from app.providers.video.wan import WanVideoProvider
from app.providers.video.veo import GoogleVeoVideoProvider
from app.web.server import GenerateRequest
from app.factory import VietnameseVideoFactory
from app.config import settings
from app.core.state_manager import ProjectStateManager


def analysis(scene_id, organ, process, setup, action, reaction, objects, cause=None, effect=None,
             environment="ORGAN_ROOM", secondary=None):
    return HealthSemanticAnalysis(
        scene_id=scene_id, primary_subject=organ, secondary_subjects=secondary or [],
        process=process, condition_state="as narrated, no unsupported disease progression",
        cause=cause, effect=effect, visual_action=action, character_emotion="focused then reacts appropriately",
        required_objects=objects, environment=environment,
        micro_story={"setup": setup, "action": action, "reaction": reaction},
        subject_movement=action, environment_movement="Relevant particles move through the readable body environment",
        biological_concept=action, visual_metaphor="Particles and expressive gestures illustrate the real biological process",
    )


def quality_analyses(case):
    if case == "liver":
        return [
            analysis(1, "liver", "normal_processing", "Healthy liver receives substances from blood",
                     "Liver processes a manageable incoming stream", "Liver remains calmly focused", ["blood stream", "substance particles"]),
            analysis(2, "liver", "alcohol_arrival", "Same liver waits beside blood vessels",
                     "Alcohol-related particles arrive through blood", "Liver notices incoming particles", ["alcohol particles", "blood stream"], cause="alcohol absorption"),
            analysis(3, "liver", "alcohol_metabolism", "Alcohol particles enter the same liver",
                     "Liver processes increasing alcohol workload", "Liver works harder and looks strained",
                     ["alcohol particles"], cause="excess alcohol", effect="increased liver workload"),
            analysis(4, "liver", "metabolic_stress", "Liver processes alcohol particles",
                     "Alcohol metabolism products may stress liver cells", "Liver becomes concerned with subtle cellular stress",
                     ["metabolic products", "liver cells"], cause="alcohol metabolism products", effect="possible liver cell stress"),
            analysis(5, "liver", "fat_accumulation", "Same liver with a readable cutaway",
                     "Yellow fat droplets gradually accumulate inside the liver over time", "Liver notices gradual fat buildup and becomes concerned",
                     ["yellow fat droplets"], cause="excess alcohol over time", effect="possible liver fat buildup"),
        ]
    if case == "kidney":
        return [
            analysis(1, "kidney", "blood_arrival", "Two recognizable kidneys beside incoming vessel",
                     "Blood flows into both kidneys", "Kidneys focus on incoming blood", ["blood stream"], environment="BLOODSTREAM_WORLD"),
            analysis(2, "kidney", "filtration_reabsorption", "Blood enters readable kidney filtration cutaways",
                     "Kidneys separate waste and excess water then reabsorb necessary substances", "Cleaned stream exits filtration",
                     ["waste particles", "blood stream", "excess water"], environment="BLOODSTREAM_WORLD"),
            analysis(3, "kidney", "filtered_blood_return", "Kidney filtration has separated waste",
                     "Cleaned blood returns to circulation while waste enters urine through ureters", "Kidneys finish filtration with two separate outgoing streams",
                     ["cleaned blood", "waste particles", "urine stream"], environment="BLOODSTREAM_WORLD"),
        ]
    return [
        analysis(1, "stomach", "food_entry", "J-shaped stomach connected to esophagus",
                 "Food enters the stomach through the esophagus", "Stomach prepares to digest food", ["food pieces", "esophagus"], environment="DIGESTIVE_WORLD"),
        analysis(2, "stomach", "acid_enzyme_digestion", "Food inside readable stomach cutaway",
                 "Stomach releases controlled digestive acid and enzymes to break down food", "Food starts breaking down while stomach remains focused",
                 ["food pieces", "digestive acid", "enzyme particles"], environment="DIGESTIVE_WORLD"),
        analysis(3, "stomach", "mixing_transit", "Food and digestive juices inside stomach",
                 "Stomach contracts to mix food and passes the mixture into the small intestine", "Mixed food leaves through pyloric outlet",
                 ["food mixture", "digestive juices"], environment="DIGESTIVE_WORLD", secondary=["intestines"]),
    ]


def score(total=100, **kwargs):
    return RelevanceScore(primary_subject_match=30, biological_process_match=30 if total == 100 else 5,
                          cause_effect_match=20, action_match=10, visual_clarity=10,
                          explanation="Direct narration-driven subject, process and causal action", **kwargs)


class HealthVisualTests(unittest.IsolatedAsyncioTestCase):
    async def test_three_quality_cases_have_causal_actions_and_stable_organs(self):
        for case in ("liver", "kidney", "stomach"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                script = quality_script(case)
                analyses = quality_analyses(case)
                llm = MagicMock()
                llm.complete_json = AsyncMock(side_effect=[
                    {"scenes": [item.model_dump() for item in analyses]},
                    *[score().model_dump() for _ in analyses],
                ])
                storyboard, bible, plans = await HealthVisualPlanner(llm).plan(script, Path(directory))
                self.assertEqual(len(storyboard.scenes), len(script.scenes))
                anchor = bible.characters[case].anchor()
                for scene in storyboard.scenes:
                    self.assertIn(anchor, scene.image_prompt)
                    self.assertIn(anchor, scene.video_prompt)
                    for label in ("SETUP:", "ACTION:", "REACTION:", "SUBJECT MOVEMENT:",
                                  "ENVIRONMENT MOVEMENT:", "CAMERA MOVEMENT:"):
                        self.assertIn(label, scene.video_prompt)
                    positive = scene.video_prompt.split("NEGATIVE:")[0].lower()
                    for bad in ("doctor", "hospital", "salad", "restaurant", "person drinking"):
                        self.assertNotIn(bad, positive)
                    debug = json.loads((Path(directory) / "health_debug" / f"scene_{scene.scene_id:03d}.json").read_text(encoding="utf-8"))
                    self.assertTrue(debug["accepted"])
                    self.assertEqual(debug["narration"], script.scenes[scene.scene_id - 1].narration)
                combined = " ".join(plan.video_prompt for plan in plans.values()).lower()
                expected = {"liver": ["alcohol", "workload", "stress", "fat droplets"],
                            "kidney": ["blood", "waste", "reabsorb", "cleaned", "ureters"],
                            "stomach": ["food", "acid", "enzymes", "contracts", "pyloric"]}[case]
                for word in expected:
                    self.assertIn(word, combined)

    async def test_analyzer_uses_exact_narration_not_old_bad_visual(self):
        script = quality_script("kidney")
        script.scenes[0].visual = "doctor in hospital with healthy salad"
        llm = MagicMock(complete_json=AsyncMock(return_value={"scenes": [s.model_dump() for s in quality_analyses("kidney")]}))
        await HealthVisualAnalyzer(llm).analyze(script)
        prompt = llm.complete_json.call_args.args[0]
        self.assertIn(script.scenes[0].narration, prompt)
        self.assertNotIn(script.scenes[0].visual, prompt)

    async def test_low_score_regenerates_and_keeps_failed_debug_attempt(self):
        script = quality_script("liver")
        script.scenes = script.scenes[:1]
        result = {"scenes": [quality_analyses("liver")[0].model_dump()]}
        llm = MagicMock(complete_json=AsyncMock(side_effect=[result, score(75).model_dump(), result, score().model_dump()]))
        with tempfile.TemporaryDirectory() as directory:
            await HealthVisualPlanner(llm).plan(script, Path(directory))
            debug = json.loads((Path(directory) / "health_debug" / "scene_001.json").read_text(encoding="utf-8"))
            self.assertEqual([a["relevance_score"] for a in debug["attempts"]], [75, 100])
            self.assertIn("score 75", llm.complete_json.call_args_list[2].args[0])

    async def test_generic_visual_hard_rejection_even_with_high_score(self):
        script = quality_script("liver")
        script.scenes = script.scenes[:1]
        result = {"scenes": [quality_analyses("liver")[0].model_dump()]}
        bad = score(unrelated_generic_visuals=["doctor in hospital"]).model_dump()
        llm = MagicMock(complete_json=AsyncMock(side_effect=[result, bad] * 3))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "rejected after 3"):
                await HealthVisualPlanner(llm).plan(script, Path(directory))

    async def test_missing_scene_analysis_is_rejected(self):
        llm = MagicMock(complete_json=AsyncMock(return_value={"scenes": []}))
        with self.assertRaisesRegex(ValueError, "every narration scene ID"):
            await HealthVisualAnalyzer(llm).analyze(quality_script("liver"))

    def test_multiple_organs_and_explicit_generic_exception(self):
        item = analysis(7, "brain", "neural_signal", "Brain beside neural pathway",
                        "Brain sends a neural signal and heart receives it then beats faster",
                        "Heart accelerates after receiving signal", ["neural signal"], secondary=["heart"], environment="NERVOUS_SYSTEM_WORLD")
        item.allowed_generic_visuals = ["doctor"]
        item.forbidden_generic_visuals = ["doctor", "hospital"]
        bible = HealthCharacterRegistry.bible(["brain", "heart"])
        image, video, negative = build_health_prompts(item, bible)
        self.assertIn(bible.characters["brain"].anchor(), image)
        self.assertIn(bible.characters["heart"].anchor(), video)
        self.assertNotIn("no unrelated doctor", negative)
        self.assertIn("no unrelated hospital", negative)

    def test_detection_and_manual_overrides_do_not_change_non_health(self):
        for text in ("galaxy and black holes", "organic farming", "technology laboratory", "ngân hà và Trái Đất",
                     "blood moon", "heart of the galaxy", "eye of the storm", "computer sleep mode"):
            self.assertEqual(resolve_visual_mode(text), VisualMode.STANDARD)
        for text in ("Thận lọc chất thải từ máu", "cholesterol", "blood pressure", "glucose", "hydration"):
            self.assertEqual(resolve_visual_mode(text), VisualMode.HEALTH_CHARACTER)
        self.assertEqual(detected_organs("organic"), [])
        self.assertEqual(resolve_visual_mode("liver", "STANDARD"), VisualMode.STANDARD)
        self.assertEqual(resolve_visual_mode("unusual narration", "health_character"), VisualMode.HEALTH_CHARACTER)
        self.assertEqual(GenerateRequest(topic="health", visual_mode="HEALTH_CHARACTER").visual_mode, VisualMode.HEALTH_CHARACTER)
        self.assertEqual(ProjectConfig(project_id="legacy", topic="galaxy").visual_mode, VisualMode.AUTO)

    def test_registry_has_eleven_recognizable_organs_and_independent_definitions(self):
        organs = ["heart", "liver", "kidney", "stomach", "lungs", "brain", "intestines", "pancreas", "bladder", "eye", "tooth"]
        bible = HealthCharacterRegistry.bible(organs)
        self.assertEqual(len(bible.characters), 11)
        for organ, character in bible.characters.items():
            self.assertIn(organ, character.anchor())
            self.assertIn("no human", character.negative_constraints)
        changed = HealthCharacterRegistry.get_character("liver")
        changed.color = "blue"
        self.assertEqual(HealthCharacterRegistry.get_character("liver").color, "reddish brown")

    async def test_health_images_never_search_stock_on_failure(self):
        provider = RealVisualMediaEngine()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(provider, "generate_ai_visual", return_value=False), \
                patch.object(provider, "search_wikimedia_image") as search:
            with self.assertRaisesRegex(RuntimeError, "stock search is prohibited"):
                await provider.generate_health_image("liver character", str(Path(directory) / "image.png"))
            search.assert_not_called()

    async def test_wan_health_path_never_downgrades_to_camera_motion(self):
        provider = WanVideoProvider()
        provider.fal_key = provider.replicate_token = None
        with self.assertRaisesRegex(RuntimeError, "Still-image motion fallback is prohibited"):
            await provider.generate_health_video(image_path="liver.png", prompt="liver processes alcohol",
                                                 output_path="test.mp4", duration_seconds=5)

    def test_preflight_rejects_static_motion_provider(self):
        generator = HealthVisualGenerator(OfflineBrainProvider(), RealVisualMediaEngine(),
                                          SemanticMotionVideoEngine(), image_model="explicit")
        with self.assertRaisesRegex(RuntimeError, "actual biological animation"):
            generator.preflight()

    async def test_gemini_health_uses_reference_bytes_without_photorealistic_prefix(self):
        provider = GeminiImagenProvider.__new__(GeminiImagenProvider)
        provider.model = "gemini-test-image"
        provider.client = MagicMock()
        from types import SimpleNamespace
        provider.client.models.generate_content.return_value = SimpleNamespace(candidates=[
            SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(inline_data=SimpleNamespace(data=b"image bytes"))]))
        ])
        with tempfile.TemporaryDirectory() as directory:
            reference = Path(directory) / "liver.png"
            reference.write_bytes(b"reference bytes")
            output = Path(directory) / "scene.png"
            await provider.generate_health_image("3D liver processes alcohol", str(output), reference_images=[str(reference)])
            contents = provider.client.models.generate_content.call_args.kwargs["contents"]
            self.assertEqual(contents[0], "3D liver processes alcohol")
            self.assertEqual(contents[1].inline_data.data, b"reference bytes")
            self.assertEqual(output.read_bytes(), b"image bytes")

    def test_high_scoring_medical_contradiction_is_rejected(self):
        self.assertFalse(score(contradicts_narration=True).accepted)
        self.assertTrue(score().accepted)

    def test_uncertain_process_fallback_does_not_invent_cause_or_broll(self):
        item = analysis(1, "liver", "contextual_organ_response", "Same liver in a clean body setting",
                        "Liver looks thoughtful and gently gestures", "Liver responds calmly without showing disease",
                        [], cause=None, effect=None)
        item.uncertainty = "Narration does not establish a biological mechanism"
        item.forbidden_generic_visuals = []
        image, video, negative = build_health_prompts(item, HealthCharacterRegistry.bible(["liver"]))
        self.assertIn("none stated; do not invent one", video)
        self.assertIn(item.uncertainty, image)
        self.assertIn("no unrelated doctor", negative)
        self.assertIn("no unrelated hospital", negative)

    async def test_reference_is_stored_and_reused_without_redesign(self):
        from PIL import Image
        generator = HealthVisualGenerator.__new__(HealthVisualGenerator)
        generator.image_provider = MagicMock(supports_health_characters=True)
        generator.video_provider = MagicMock(supports_health_animation=True)
        async def image(prompt, output, *args, **kwargs):
            Image.new("RGB", (32, 32), "brown").save(output)
            return output
        generator.image_provider.generate_health_image = AsyncMock(side_effect=image)
        generator._review_image = AsyncMock(return_value=CharacterReview(
            recognizable_organ=True, organ_is_character=True, consistent_design=True,
            relevant_setup=True, explanation="Approved reference",
        ))
        bible = HealthCharacterRegistry.bible(["liver"])
        with tempfile.TemporaryDirectory() as directory:
            await generator.generate_references(bible, Path(directory), 32, 32)
            reference = Path(bible.characters["liver"].reference_image)
            original = reference.read_bytes()
            await generator.generate_references(bible, Path(directory), 32, 32)
            self.assertEqual(original, reference.read_bytes())
            generator.image_provider.generate_health_image.assert_awaited_once()
            self.assertTrue((Path(directory) / "health_character_bible.json").exists())

    async def test_unrelated_generated_image_is_rejected_before_video(self):
        from PIL import Image
        generator = HealthVisualGenerator.__new__(HealthVisualGenerator)
        generator.image_provider = MagicMock(supports_reference_images=True)
        async def image(prompt, output, *args, **kwargs):
            Image.new("RGB", (32, 32), "white").save(output)
        generator.image_provider.generate_health_image = AsyncMock(side_effect=image)
        generator.video_provider = MagicMock(generate_health_video=AsyncMock())
        generator._review_image = AsyncMock(return_value=CharacterReview(
            recognizable_organ=False, organ_is_character=False, consistent_design=False,
            relevant_setup=False, explanation="Image shows a doctor instead of kidney filtration",
        ))
        item = quality_analyses("kidney")[1]
        bible = HealthCharacterRegistry.bible(["kidney"])
        prompts = build_health_prompts(item, bible)
        plan = HealthScenePlan(analysis=item, image_prompt=prompts[0], video_prompt=prompts[1],
                               negative_prompt=prompts[2], relevance=score())
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            reference = directory / "kidney.png"
            Image.new("RGB", (32, 32), "brown").save(reference)
            bible.characters["kidney"].reference_image = str(reference)
            save_json(directory / "health_debug" / "scene_002.json", {"narration": "Kidneys filter waste"})
            with self.assertRaisesRegex(RuntimeError, "unrelated/inconsistent"):
                await generator.generate_scene("Kidneys filter waste", plan, bible, directory, directory, 5, 32, 32)
            generator.video_provider.generate_health_video.assert_not_called()
            self.assertEqual(generator.image_provider.generate_health_image.await_count, 2)

    async def test_veo_strict_health_uses_valid_duration_and_downloads_uri_result(self):
        from types import SimpleNamespace
        provider = GoogleVeoVideoProvider.__new__(GoogleVeoVideoProvider)
        provider.model = "veo-test"
        provider.client = MagicMock()
        provider.motion_engine = MagicMock(generate_image_to_video=AsyncMock())
        provider.client.models.generate_videos.return_value = SimpleNamespace(
            done=True, result=None,
            response=SimpleNamespace(generated_videos=[SimpleNamespace(video=SimpleNamespace(video_bytes=None))]),
        )
        provider.client.files.download.return_value = b"video bytes"
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "reference.png"
            image.write_bytes(b"image bytes")
            output = Path(directory) / "scene.mp4"
            await provider.generate_health_video(image_path=str(image), prompt="Kidneys filter waste",
                                                  output_path=str(output), duration_seconds=5.3)
            config = provider.client.models.generate_videos.call_args.kwargs["config"]
            self.assertEqual(config.duration_seconds, 6)
            self.assertFalse(config.generate_audio)
            self.assertEqual(output.read_bytes(), b"video bytes")
            provider.motion_engine.generate_image_to_video.assert_not_called()

    async def test_veo_health_errors_never_become_still_motion(self):
        provider = GoogleVeoVideoProvider.__new__(GoogleVeoVideoProvider)
        provider.model = "veo-test"
        provider.client = MagicMock()
        provider.client.models.generate_videos.side_effect = RuntimeError("quota unavailable")
        provider.motion_engine = MagicMock(generate_image_to_video=AsyncMock())
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "reference.png"
            image.write_bytes(b"image bytes")
            with self.assertRaisesRegex(RuntimeError, "no still-image or stock fallback"):
                await provider.generate_health_video(image_path=str(image), prompt="Stomach digests food",
                                                      output_path=str(Path(directory) / "video.mp4"), duration_seconds=5)
            provider.motion_engine.generate_image_to_video.assert_not_called()

    async def test_factory_routes_health_and_preserves_non_health_storyboarding(self):
        for health in (False, True):
            with self.subTest(health=health), tempfile.TemporaryDirectory() as directory:
                script = quality_script("liver") if health else StructuredScript(
                    title="The galaxy", hook="Explore stars", target_duration=30,
                    scenes=[SceneScript(id=1, narration="A galaxy contains billions of stars.",
                                        visual="Spiral galaxy", estimated_duration=5)],
                )
                storyboard = await OfflineBrainProvider().generate_storyboard(script)
                llm = MagicMock(research_topic=AsyncMock(return_value={}),
                                generate_script=AsyncMock(return_value=script),
                                generate_storyboard=AsyncMock(return_value=storyboard))
                with patch.object(settings, "PROJECTS_DIR", Path(directory)), \
                        patch("app.factory.get_llm_provider", return_value=llm), \
                        patch("app.factory.get_image_provider", return_value=MagicMock()), \
                        patch("app.factory.get_video_provider", return_value=MagicMock()), \
                        patch("app.factory.get_tts_provider", return_value=MagicMock()), \
                        patch("app.factory.HealthVisualPlanner") as planner_type, \
                        patch("app.factory.HealthVisualGenerator") as generator_type:
                    bible = HealthCharacterRegistry.bible(["liver"])
                    plans = {item.scene_id: HealthScenePlan(
                        analysis=item, image_prompt=build_health_prompts(item, bible)[0],
                        video_prompt=build_health_prompts(item, bible)[1],
                        negative_prompt=build_health_prompts(item, bible)[2], relevance=score(),
                    ) for item in quality_analyses("liver")}
                    planner_type.return_value.plan = AsyncMock(return_value=(storyboard, bible, plans))
                    generator_type.return_value.generate_references = AsyncMock()
                    factory = VietnameseVideoFactory(console_output=False)
                    factory.timeline_engine.build_timeline = AsyncMock(side_effect=RuntimeError("timeline test stop"))
                    with self.assertRaisesRegex(RuntimeError, "timeline test stop"):
                        await factory.generate_video("Liver alcohol metabolism" if health else "Galaxy formation", project_id="routing")
                    state = ProjectStateManager("routing").load_state()
                    self.assertEqual(state.config.visual_mode, VisualMode.HEALTH_CHARACTER if health else VisualMode.STANDARD)
                    if health:
                        llm.generate_storyboard.assert_not_called()
                        planner_type.return_value.plan.assert_awaited_once()
                        generator_type.return_value.generate_references.assert_awaited_once()
                    else:
                        llm.generate_storyboard.assert_awaited_once()
                        planner_type.assert_not_called()
                        generator_type.assert_not_called()


if __name__ == "__main__":
    unittest.main()
