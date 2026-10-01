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

    def _call_chat_completions(self, messages: list, json_mode: bool = True):
        preferred = [self.model, "gpt-4o", "gpt-4o-mini"]
        candidates = []
        for m in preferred:
            if m and m not in candidates:
                candidates.append(m)
        last_error = None
        for m in candidates:
            try:
                kwargs = {
                    "model": m,
                    "messages": messages
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                return self.client.chat.completions.create(**kwargs)
            except Exception as e:
                last_error = e
                continue
        raise last_error

    async def research_topic(self, topic: str) -> Dict[str, Any]:
        prompt = f"""Bạn là chuyên gia nghiên cứu tài liệu video khoa học và khám phá.
Chủ đề: "{topic}"
Trả về JSON gồm 3 facts kỳ thú, core_angle và emotional_hook."""
        response = self._call_chat_completions(messages=[{"role": "user", "content": prompt}])
        return json.loads(RobustJSONParser.extract_json_str(response.choices[0].message.content))

    async def generate_script(
        self,
        topic: str,
        target_duration: int = 60,
        platform: str = "tiktok",
        language: str = "vi"
    ) -> StructuredScript:
        num_scenes = max(5, min(12, int(target_duration / 6)))
        prompt = f"""Bạn là đạo diễn và biên kịch video viral hàng đầu trên {platform}.
Nhiệm vụ: Viết kịch bản video tiếng Việt hoàn chỉnh cho chủ đề: "{topic}".
Tổng thời lượng: {target_duration}s, phân rã thành {num_scenes} cảnh.

Yêu cầu cấu trúc BẮT BUỘC:
1. CẢNH 1 (INTRO MỞ ĐẦU): Hook giật gân, câu hỏi kích thích tò mò cao độ trong 3-5s đầu, visual tráng lệ.
2. THÂN BÀI: Trình bày kịch tính, lôi cuốn, ngắt câu rõ ràng, không sáo rỗng.
3. CẢNH CUỐI (OUTRO & KÊU GỌI HÀNH ĐỘNG): Đúc kết thông điệp + câu kêu gọi hành động (Call To Action - CTA): Bấm Like và Theo dõi kênh để xem các tập tiếp theo.

Trả về JSON theo schema StructuredScript:
{{
  "title": "Tiêu đề video",
  "hook": "Câu mở đầu 3s đầu",
  "target_duration": {target_duration},
  "language": "{language}",
  "scenes": [
    {{
      "id": 1,
      "narration": "Lời thuyết minh INTRO mở đầu tiếng Việt...",
      "visual": "Mô tả bối cảnh hình ảnh INTRO...",
      "estimated_duration": 5.0,
      "camera_motion": "slow zoom in",
      "transition": "fade in",
      "sound_effect": "whoosh"
    }},
    {{
      "id": {num_scenes},
      "narration": "Lời thuyết minh OUTRO kết thúc và kêu gọi theo dõi kênh...",
      "visual": "Mô tả bối cảnh hình ảnh OUTRO...",
      "estimated_duration": 5.0,
      "camera_motion": "slow pull back",
      "transition": "fade to black",
      "sound_effect": "outro impact"
    }}
  ]
}}"""
        response = self._call_chat_completions(messages=[{"role": "user", "content": prompt}])
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
        response = self._call_chat_completions(messages=[{"role": "user", "content": prompt}])
        return RobustJSONParser.parse_to_model(response.choices[0].message.content, Storyboard)

    async def generate_metadata(
        self,
        topic: str,
        script: StructuredScript
    ) -> Dict[str, Any]:
        prompt = f"Tạo metadata mạng xã hội tiếng Việt cho video: {script.title} - {topic}. Trả về JSON."
        response = self._call_chat_completions(messages=[{"role": "user", "content": prompt}])
        return json.loads(RobustJSONParser.extract_json_str(response.choices[0].message.content))
