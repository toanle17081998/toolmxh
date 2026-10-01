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

    async def generate_script(
        self,
        topic: str,
        target_duration: int = 60,
        platform: str = "tiktok",
        language: str = "vi"
    ) -> StructuredScript:
        # Số lượng scene lý tưởng: mỗi scene 4-7s, với video 60s thì cần khoảng 8-12 scenes
        num_scenes = max(5, min(12, int(target_duration / 6)))
        prompt = f"""Bạn là Bậc Thầy Kể Chuyện và Đạo Diễn Biên Kịch hàng đầu cho các kênh triệu view trên {platform} (phong cách cuốn hút như Netflix Documentary, Kurzgesagt, Monster Box).
Nhiệm vụ: Viết kịch bản video tiếng Việt ĐỈNH CAO, CỰC KỲ CUỐN HÚT cho chủ đề: "{topic}".
Tổng thời lượng mục tiêu: {target_duration} giây.
Số cảnh phân rã: {num_scenes} cảnh (mỗi cảnh từ 4 đến 7 giây).

TIÊU CHUẨN BIÊN KỊCH TRIỆU VIEW (BẮT BUỘC TUÂN THỦ):
1. CẢNH 1 - HOOK GIẬT TÍT ĐỈNH CAO (3-5 GIÂY ĐẦU):
   - Tuyệt đối KHÔNG dùng văn mẫu sáo rỗng như: "Bạn có bao giờ tự hỏi...", "Chào mừng các bạn...", "Hôm nay chúng ta sẽ tìm hiểu...".
   - Hãy mở đầu bằng MỘT TUYÊN BỐ GÂY SỐC, MỘT NGHỊCH LÝ ĐIÊN RỒ, hoặc MỘT HẬU QUẢ TẬN THẾ trực diện đánh thẳng vào người xem.
   - Khiến người xem dừng ngón tay lại ngay giây đầu tiên vì quá tò mò.

2. CÁC CẢNH THÂN BÀI - NGHỆ THUẬT DỒN DẬP & VÒNG LẶP TÒ MÒ (CURIOSITY LOOP):
   - Ngôn từ giàu hình ảnh, nhịp điệu nhanh, sắc bén, dứt khoát.
   - Mỗi cảnh hé lộ một sự thật không ngờ, đẩy kịch tính lên cao trào (Climax).
   - Lời thuyết minh (narration) viết bằng tiếng Việt tự nhiên, có hồn, ngắt nghỉ câu chuẩn xác để AI đọc truyền cảm.

3. CẢNH CUỐI CÙNG - NÚT THẮT SÂU SẮC & CALL TO ACTION KÍCH HOẠT THUẬT TOÁN:
   - Đưa ra một câu hỏi mở gây tranh cãi kích thích người xem phải bình luận ngay.
   - Lời kêu gọi hành động (CTA) khéo léo, tự nhiên: "Bấm Like và Theo dõi kênh để không bỏ lỡ những bí ẩn chấn động tiếp theo!"

Tuân thủ định dạng JSON theo schema:
{{
  "title": "Tiêu đề video giật gân, chuẩn SEO triệu view",
  "hook": "Câu Hook gây sốc trong 3 giây đầu",
  "target_duration": {target_duration},
  "language": "{language}",
  "scenes": [
    {{
      "id": 1,
      "narration": "Lời thuyết minh INTRO mở đầu tiếng Việt...",
      "visual": "Mô tả bối cảnh hình ảnh INTRO...",
      "estimated_duration": 5.0,
      "camera_motion": "dramatic fast zoom in / whip pan",
      "transition": "fade in",
      "sound_effect": "heavy cinematic bass drop impact"
    }},
    {{
      "id": {num_scenes},
      "narration": "Lời thuyết minh OUTRO kết thúc và kêu gọi theo dõi kênh...",
      "visual": "Mô tả bối cảnh hình ảnh OUTRO...",
      "estimated_duration": 5.0,
      "camera_motion": "slow pull back to epic wide shot",
      "transition": "fade to black",
      "sound_effect": "suspenseful outro crescendo"
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
