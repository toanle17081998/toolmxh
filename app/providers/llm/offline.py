from typing import Dict, Any, Optional

from app.providers.llm.base import LLMProvider
from app.models.script import StructuredScript
from app.models.storyboard import Storyboard, SceneStoryboard, VisualStyleBible


class OfflineBrainProvider(LLMProvider):
    """Offline formatting of existing content; topic research requires a real LLM."""

    @staticmethod
    def _unavailable():
        raise RuntimeError(
            "Không có LLM khả dụng để tạo nội dung đúng chủ đề. "
            "Hãy cấu hình GEMINI_API_KEY hoặc OPENAI_API_KEY và kiểm tra model/quota. "
            "Đã dừng tạo video để tránh dùng kịch bản mẫu không liên quan."
        )

    async def research_topic(self, topic: str) -> Dict[str, Any]:
        self._unavailable()

    async def generate_script(
        self,
        topic: str,
        target_duration: int = 60,
        platform: str = "tiktok",
        language: str = "vi",
        mascot_id: Optional[str] = "dr_bear",
    ) -> StructuredScript:
        self._unavailable()

    async def generate_storyboard(
        self,
        script: StructuredScript,
        visual_bible: Optional[VisualStyleBible] = None,
        mascot_id: Optional[str] = "dr_bear",
    ) -> Storyboard:
        vb = visual_bible or VisualStyleBible()
        scenes = []
        for scene in script.scenes:
            scenes.append(SceneStoryboard(
                scene_id=scene.id,
                duration=scene.estimated_duration,
                narration=scene.narration,
                subject=scene.visual,
                environment=f"Setting for {script.title}",
                lighting=vb.lighting,
                camera_angle="cinematic dynamic angle",
                camera_movement=scene.camera_motion,
                visual_style=vb.style,
                image_prompt=f"{scene.visual}, {vb.style}, {vb.lighting}, {vb.lens}, {vb.contrast}",
                video_prompt=f"{scene.visual}. Camera movement: {scene.camera_motion}; continuous coherent motion.",
                negative_prompt="ugly, distorted, blurry, low quality, artifacts, watermark, text",
                transition=scene.transition,
                sound_effect=scene.sound_effect,
            ))
        return Storyboard(project_id="temp", visual_bible=vb, scenes=scenes)

    async def generate_metadata(self, topic: str, script: StructuredScript) -> Dict[str, Any]:
        return {
            "tiktok_caption": script.hook,
            "youtube_title": script.title,
            "youtube_description": "\n".join(scene.narration for scene in script.scenes),
            "facebook_caption": script.hook,
            "hashtags": [],
            "keywords": [topic],
            "thumbnail_text": script.title,
        }
