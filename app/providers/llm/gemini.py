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
        """Gọi Gemini API với cơ chế tự động hạ cấp model nếu gặp 404/503/429."""
        preferred_list = [self.model, "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-pro-preview", "gemini-2.5-flash", "gemini-flash-latest"]
        candidate_models = []
        for m in preferred_list:
            if m and m not in candidate_models:
                candidate_models.append(m)

        last_error = None
        for m in candidate_models:
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

    async def complete_json(self, prompt: str, image_paths=None, schema=None) -> Dict[str, Any]:
        import asyncio
        from pathlib import Path
        contents = [prompt]
        for path in image_paths or []:
            contents.append(types.Part.from_bytes(data=Path(path).read_bytes(), mime_type="image/png"))
        response = await asyncio.to_thread(
            self._call_generate_content, contents,
            types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=schema),
        )
        return json.loads(response.text)

    async def generate_script(
        self,
        topic: str,
        target_duration: int = 60,
        platform: str = "tiktok",
        language: str = "vi",
        mascot_id: Optional[str] = "dr_bear"
    ) -> StructuredScript:
        from app.models.mascot import get_mascot
        mascot = get_mascot(mascot_id)

        # Số lượng scene lý tưởng: mỗi scene 4-7s, với video 60s thì cần khoảng 8-12 scenes
        num_scenes = max(5, min(12, int(target_duration / 6)))
        prompt = f"""Bạn là Bậc Thầy Biên Kịch Phim Hoạt Hình 3D Dẫn Chuyện Hàng Đầu (phong cách Pixar Kurzgesagt triệu view).
Chủ đề: "{topic}".
Tổng thời lượng mục tiêu: {target_duration} giây.
Số cảnh phân rã: {num_scenes} cảnh (mỗi cảnh từ 4 đến 7 giây).

🌟 LINH VẬT DẪN CHUYỆN XUYÊN SUỐT VIDEO:
- Nhân vật: {mascot.name} ({mascot.role_title})
- Tính cách & Cách kể: {mascot.persona_prompt}
- YÊU CẦU CỐT LÕI: Toàn bộ kịch bản là lời kể trực tiếp của {mascot.name}. Hãy dùng ngôi xưng thân thiện, biểu cảm hài hước, giải thích khoa học sức khỏe dễ hiểu bằng hình ảnh trực quan, đánh thức sự tò mò của người xem!

TIÊU CHUẨN BIÊN KỊCH TRIỆU VIEW (BẮT BUỘC TUÂN THỦ):
1. CẢNH 1 - HOOK GIẬT TÍT & LINH VẬT XUẤT HIỆN:
   - {mascot.name} đưa ra một sự thật sức khỏe / nghịch lý giật mình, cảnh báo người xem ngay giây đầu tiên.
2. CÁC CẢNH THÂN BÀI - HÀNH TRÌNH KHÁM PHÁ CỦA LINH VẬT:
   - {mascot.name} dẫn dắt người xem đi soi vào từng bộ phận cơ thể hoặc giải mã thói quen, giải thích nguyên nhân và hệ quả sinh học thú vị.
   - Ngôn từ tự nhiên, ngắt nghỉ câu chuẩn để AI đọc lôi cuốn.
3. CẢNH CUỐI - LỜI KHUYÊN ẤM ÁP & KÊU GỌI FOLLOW:
   - {mascot.name} đưa ra lời khuyên thiết thực và mời mọi người bấm Like, Follow kênh để đồng hành cùng {mascot.name}!

Tuân thủ định dạng JSON theo schema:
{{
  "title": "Tiêu đề video chuẩn SEO lôi cuốn",
  "hook": "Câu Hook gây sốc của {mascot.name}",
  "target_duration": {target_duration},
  "language": "{language}",
  "scenes": [
    {{
      "id": 1,
      "narration": "Lời dẫn chuyện của {mascot.name} ở cảnh mở đầu...",
      "visual": "Mô tả {mascot.name} đang làm gì trong bối cảnh...",
      "estimated_duration": 5.0,
      "camera_motion": "dynamic push in to mascot",
      "transition": "fade in",
      "sound_effect": "playful cartoon pop"
    }},
    {{
      "id": {num_scenes},
      "narration": "Lời khuyên kết thúc và lời chào của {mascot.name}...",
      "visual": "Mô tả {mascot.name} vẫy tay chào tạm biệt...",
      "estimated_duration": 5.0,
      "camera_motion": "slow pull back",
      "transition": "fade to black",
      "sound_effect": "warm cheerful outro chime"
    }}
  ]
}}"""
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
        visual_bible: Optional[VisualStyleBible] = None,
        mascot_id: Optional[str] = "dr_bear"
    ) -> Storyboard:
        from app.models.mascot import get_mascot
        mascot = get_mascot(mascot_id)
        vb = visual_bible or VisualStyleBible()
        vb.style = f"3D Pixar Animation ({mascot.name})"

        prompt = f"""Bạn là Đạo diễn Hoạt Hình 3D (3D Animation Director) của Pixar / Disney.
Kịch bản phim hoạt hình:
Title: {script.title}
Hook: {script.hook}
Scenes:
{script.model_dump_json(indent=2)}

🌟 LINH VẬT CỐ ĐỊNH XUYÊN SUỐT TẤT CẢ CÁC CẢNH (CHARACTER CONSISTENCY):
- Ngoại hình gốc của {mascot.name}: "{mascot.visual_anchor}"
- Phong cách nghệ thuật: "{mascot.style_suffix}"

QUY TẮC BẮT BUỘC KHI SINH IMAGE_PROMPT CHO MỖI CẢNH:
1. MỖI CẢNH PHẢI CÓ {mascot.name} LÀ CHỦ THỂ TRUNG TÂM!
2. Bắt đầu 'image_prompt' bằng: "{mascot.visual_anchor}".
3. Miêu tả hành động, tư thế và biểu cảm cụ thể của {mascot.name} trong cảnh đó (ví dụ: đang cầm kính lúp soi lá gan 3D ngạc nhiên, đang chỉ que bảng vào ly nước ấm, đang lắc đầu cảnh báo đồ ăn ngọt, đang vui vẻ tập thể dục...).
4. Miêu tả bối cảnh xung quanh theo phong cách hoạt hình 3D dễ thương, sinh động.
5. Kết thúc bằng: "{mascot.style_suffix}".

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
      "subject": "{mascot.name}",
      "environment": "3D stylized medical laboratory or health environment",
      "lighting": "warm soft studio lighting",
      "camera_angle": "medium close-up on mascot",
      "camera_movement": "gentle forward push in",
      "visual_style": "{vb.style}",
      "image_prompt": "{mascot.visual_anchor}, looking shocked with mouth open, pointing towards a floating 3D health icon, {mascot.style_suffix}",
      "video_prompt": "Gentle animated camera push in towards the character, subtle character blinking and nodding motion",
      "negative_prompt": "ugly, distorted, blurry, photorealistic human, dark scary, watermark",
      "transition": "cut",
      "sound_effect": "cheerful pop"
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
