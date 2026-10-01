import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.script import SceneScript, StructuredScript
from app.providers.image.real_media import RealVisualMediaEngine
from app.providers.image.dalle import OpenAIDalle3Provider
from app.providers.image.gemini_imagen import GeminiImagenProvider
from app.providers.llm.offline import OfflineBrainProvider
from app.providers.video.real_footage import RealFootageVideoEngine


class ShortContentRelevanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_offline_does_not_invent_research_or_script(self):
        provider = OfflineBrainProvider()
        for topic in ("Chăm sóc sức khỏe tim mạch", "Bí mật của máy tính"):
            with self.subTest(topic=topic):
                with self.assertRaisesRegex(RuntimeError, "LLM"):
                    await provider.research_topic(topic)
                with self.assertRaisesRegex(RuntimeError, "LLM"):
                    await provider.generate_script(topic)

    async def test_storyboard_keeps_scene_subject_in_video_prompt(self):
        script = StructuredScript(
            title="Sức khỏe tim mạch", hook="Chăm sóc trái tim", target_duration=30,
            scenes=[SceneScript(id=1, narration="Vận động mỗi ngày.",
                                visual="A doctor explaining the human heart",
                                estimated_duration=5.0)],
        )
        storyboard = await OfflineBrainProvider().generate_storyboard(script)
        self.assertIn(script.scenes[0].visual, storyboard.scenes[0].video_prompt)

    async def test_failed_image_generation_does_not_use_unrelated_fallback(self):
        provider = RealVisualMediaEngine()
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / "reference.png")
            with patch.object(provider, "generate_ai_visual", return_value=False), \
                    patch.object(provider, "search_wikimedia_image", return_value=None) as search:
                with self.assertRaisesRegex(RuntimeError, "ảnh"):
                    await provider.generate_image("Bác sĩ giải thích sức khỏe tim mạch", output, 64, 64)
                queries = [call.args[0].lower() for call in search.call_args_list]
                self.assertFalse(any("space" in q or "server" in q or "earth" in q for q in queries))
                self.assertFalse(Path(output).exists())

    def test_health_queries_preserve_subject_and_unicode(self):
        queries = RealVisualMediaEngine()._extract_keywords("Bác sĩ giải thích sức khỏe tim mạch")
        self.assertIn("human heart anatomy", queries)
        self.assertTrue(any("tim mạch" in q for q in queries))

    def test_motion_only_prompt_does_not_search_random_stock(self):
        provider = RealFootageVideoEngine()
        self.assertEqual(provider._extract_search_keywords("cinematic slow zoom in"), [])

    async def test_paid_image_failures_propagate_relevance_failure(self):
        for provider_type in (OpenAIDalle3Provider, GeminiImagenProvider):
            with self.subTest(provider=provider_type.__name__), tempfile.TemporaryDirectory() as directory:
                provider = provider_type.__new__(provider_type)
                provider.client = MagicMock()
                provider.model = "gemini-test"
                provider.client.images.generate.side_effect = RuntimeError("service unavailable")
                provider.client.models.generate_content.side_effect = RuntimeError("service unavailable")
                fallback = AsyncMock(side_effect=RuntimeError("Không tìm thấy ảnh phù hợp"))
                with patch.object(RealVisualMediaEngine, "generate_image", fallback):
                    with self.assertRaisesRegex(RuntimeError, "ảnh phù hợp"):
                        await provider.generate_image("human heart anatomy", str(Path(directory) / "image.png"))
                    fallback.assert_awaited_once_with(
                        "human heart anatomy", str(Path(directory) / "image.png"), 1080, 1920, -1,
                    )

    def test_mapping_does_not_match_organ_inside_another_word(self):
        queries = RealVisualMediaEngine()._extract_keywords("organic food")
        self.assertNotIn("human liver anatomy", queries)


if __name__ == "__main__":
    unittest.main()
