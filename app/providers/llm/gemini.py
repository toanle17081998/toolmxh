import os
import json
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from app.providers.llm.base import LLMProvider
from app.providers.llm.parser import RobustJSONParser
from app.models.script import StructuredScript
from app.models.storyboard import Storyboard, VisualStyleBible
from app.config import settings

class GeminiLLMProvider(LLMProvider):
    """Content Brain sử dụng Google Gemini 2.5 Flash / Pro."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY không được tìm thấy.")
        self.client = genai.Client(api_key=self.api_key)
        self.model = model

    def _call_generate_content(self, contents: str, config: types.GenerateContentConfig):
        """Gọi Gemini API với cơ chế tự động hạ cấp model nếu gặp 404 (model cũ) hoặc 429 (quota limit)."""
        candidate_models = [self.model, "gemini-2.5-flash", "gemini-flash-latest"]
        last_error = None
        for m in candidate_models:
            if not m:
                continue
            try:
                return self.client.models.generate_content(
                    model=m,
                    contents=contents,
                    config=config
                )
            except Exception as e:
                last_error = e
                continue
        raise last_error

    async def research_topic(self, topic: str) -> Dict[str, Any]:
        prompt = f"""Bạn là một chuyên gia nghiên cứu tài liệu video khoa học và khám phá.
Chủ đề: "{topic}"
Hãy nghiên cứu và đưa ra:
1. 3 sự thật giật gân, ít người biết nhất về chủ đề này.
2. Góc nhìn gây tò mò, kịch tính nhất để thu hút người xem mạng xã hội.
3. Cảm xúc cốt lõi video cần truyền tải (hồi hộp, kinh ngạc, sâu lắng).

Trả về định dạng JSON:
{{
  "facts": ["...", "..."],
  "core_angle": "...",
  "emotional_hook": "..."
}}
"""
        response = self._call_generate_content(
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(RobustJSONParser.extract_json_str(response.text))

    async def generate_script(
        self,
        topic: str,
        target_duration: int = 60,
        platform: str = "tiktok",
        language: str = "vi"
    ) -> StructuredScript:
        # Số lượng scene lý tưởng: mỗi scene 4-7s, với video 60s thì cần khoảng 8-12 scenes
        num_scenes = max(5, min(12, int(target_duration / 6)))
        prompt = f"""Bạn là một đạo diễn và biên kịch video viral hàng đầu trên {platform}.
Nhiệm vụ: Viết kịch bản video tiếng Việt hoàn chỉnh cho chủ đề: "{topic}".
Tổng thời lượng mục tiêu: {target_duration} giây.
Số cảnh cần phân rã: {num_scenes} cảnh (mỗi cảnh khoảng 4 đến 7 giây).

Yêu cầu nghiêm ngặt:
1. Hook (3 giây đầu) phải cực kỳ giật gân, khơi gợi tò mò tột độ.
2. Lời thuyết minh (narration) tiếng Việt phải tự nhiên, hào hùng hoặc huyền bí, ngắt câu rõ ràng, không dùng từ sáo rỗng.
3. Visual mô tả cụ thể hình ảnh hành động, ánh sáng, góc máy cho từng cảnh.
4. Tuân thủ định dạng JSON theo schema:
{{
  "title": "Tiêu đề video hấp dẫn",
  "hook": "Câu mở đầu 3s đầu",
  "target_duration": {target_duration},
  "language": "{language}",
  "scenes": [
    {{
      "id": 1,
      "narration": "Lời thuyết minh tiếng Việt của cảnh 1...",
      "visual": "Mô tả bối cảnh hình ảnh...",
      "estimated_duration": 5.0,
      "camera_motion": "slow zoom in / dramatic pan / orbit",
      "transition": "cut",
      "sound_effect": "ocean rumble / heartbeat / whoosh"
    }}
  ]
}}
"""
        response = self._call_generate_content(
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return RobustJSONParser.parse_to_model(response.text, StructuredScript)

    async def generate_storyboard(
        self,
        script: StructuredScript,
        visual_bible: Optional[VisualStyleBible] = None
    ) -> Storyboard:
        vb = visual_bible or VisualStyleBible()
        prompt = f"""Bạn là Đạo diễn Hình ảnh (Director of Photography - DOP) và Prompt Engineer điện ảnh.
Kịch bản:
Title: {script.title}
Hook: {script.hook}
Scenes:
{script.model_dump_json(indent=2)}

Phong cách thị giác chủ đạo (Visual Bible):
- Style: {vb.style}
- Lighting: {vb.lighting}
- Lens: {vb.lens}
- Render Style: {vb.render_style}

Hãy chuyển kịch bản này thành Storyboard chi tiết. Mỗi cảnh phải có:
1. `image_prompt`: Prompt tiếng Anh siêu chi tiết để mô hình AI Image (FLUX/Imagen) sinh ảnh tham chiếu (chủ thể rõ ràng, bố cục điện ảnh, ánh sáng).
2. `video_prompt`: Prompt tiếng Anh mô tả chuyển động camera và chuyển động vật thể cho mô hình Image-to-Video (I2V / Wan 2.1).
3. `camera_angle`, `camera_movement`, `lighting`, `environment`, `subject`.

Trả về định dạng JSON:
{{
  "project_id": "temp",
  "visual_bible": {vb.model_dump_json()},
  "characters": [],
  "scenes": [
    {{
      "scene_id": 1,
      "duration": 5.0,
      "narration": "...",
      "subject": "...",
      "environment": "...",
      "lighting": "...",
      "camera_angle": "wide cinematic establishing shot",
      "camera_movement": "slow forward push in",
      "visual_style": "{vb.style}",
      "image_prompt": "Cinematic 8k shot of ..., dramatic volumetric lighting, 35mm lens, highly detailed ...",
      "video_prompt": "Cinematic camera slowly pushes forward through ..., subtle atmospheric dust drift, hyper-realistic motion",
      "negative_prompt": "ugly, distorted, blurry, low quality, artifacts, watermark",
      "transition": "cut",
      "sound_effect": "deep ocean ambient"
    }}
  ]
}}
"""
        response = self._call_generate_content(
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return RobustJSONParser.parse_to_model(response.text, Storyboard)

    async def generate_metadata(
        self,
        topic: str,
        script: StructuredScript
    ) -> Dict[str, Any]:
        prompt = f"""Tạo metadata đăng tải video cho mạng xã hội TikTok, YouTube Shorts và Facebook Reels dựa trên kịch bản:
Tiêu đề: {script.title}
Hook: {script.hook}
Chủ đề: {topic}

Trả về JSON:
{{
  "tiktok_caption": "Caption ngắn có call-to-action tiếng Việt...",
  "youtube_title": "Tiêu đề chuẩn SEO YouTube...",
  "youtube_description": "Mô tả đầy đủ...",
  "facebook_caption": "Caption Facebook...",
  "hashtags": ["#fyp", "#khampha", "#khoahoc", ...],
  "keywords": ["...", "..."],
  "thumbnail_text": "Chữ ngắn gọn 3-4 từ giật gân để gắn lên thumbnail"
}}
"""
        response = self._call_generate_content(
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(RobustJSONParser.extract_json_str(response.text))
