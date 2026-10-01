import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from app.providers.llm.base import LLMProvider
from app.providers.llm.parser import RobustJSONParser
from app.models.script import StructuredScript
from app.models.storyboard import Storyboard, VisualStyleBible
from app.config import settings

class OpenAILLMProvider(LLMProvider):
    """Content Brain sử dụng OpenAI GPT-4o / GPT-4o-mini."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY không được tìm thấy.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    async def research_topic(self, topic: str) -> Dict[str, Any]:
        prompt = f"""Bạn là chuyên gia nghiên cứu tài liệu video khoa học và khám phá.
Chủ đề: "{topic}"
Trả về JSON gồm 3 facts kỳ thú, core_angle và emotional_hook."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(RobustJSONParser.extract_json_str(response.choices[0].message.content))

    async def generate_script(
        self,
        topic: str,
        target_duration: int = 60,
        platform: str = "tiktok",
        language: str = "vi"
    ) -> StructuredScript:
        num_scenes = max(5, min(12, int(target_duration / 6)))
        prompt = f"""Viết kịch bản video tiếng Việt hoàn chỉnh cho chủ đề: "{topic}".
Tổng thời lượng: {target_duration}s, phân rã thành {num_scenes} scenes.
Trả về JSON theo schema StructuredScript:
{{
  "title": "...",
  "hook": "...",
  "target_duration": {target_duration},
  "language": "{language}",
  "scenes": [
    {{
      "id": 1,
      "narration": "...",
      "visual": "...",
      "estimated_duration": 5.0,
      "camera_motion": "...",
      "transition": "cut",
      "sound_effect": "..."
    }}
  ]
}}"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return RobustJSONParser.parse_to_model(response.choices[0].message.content, StructuredScript)

    async def generate_storyboard(
        self,
        script: StructuredScript,
        visual_bible: Optional[VisualStyleBible] = None
    ) -> Storyboard:
        vb = visual_bible or VisualStyleBible()
        prompt = f"""Chuyển kịch bản sau thành Storyboard điện ảnh:
Script: {script.model_dump_json()}
Style Bible: {vb.model_dump_json()}
Trả về JSON tuân thủ schema Storyboard."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return RobustJSONParser.parse_to_model(response.choices[0].message.content, Storyboard)

    async def generate_metadata(
        self,
        topic: str,
        script: StructuredScript
    ) -> Dict[str, Any]:
        prompt = f"Tạo metadata mạng xã hội tiếng Việt cho video: {script.title} - {topic}. Trả về JSON."
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(RobustJSONParser.extract_json_str(response.choices[0].message.content))
