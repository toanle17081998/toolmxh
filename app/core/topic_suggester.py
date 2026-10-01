import os
import json
import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger("TopicSuggester")

# Kho dữ liệu chủ đề viral được tuyển chọn kỹ lưỡng chuẩn TikTok / Shorts / Reels
CURATED_TOPICS: List[Dict[str, Any]] = [
    # Vũ trụ & Khoa học
    {
        "id": "space_1",
        "category": "space",
        "category_name": "🌌 Vũ Trụ & Khoa Học",
        "title": "Bí ẩn ranh giới chân trời sự kiện của Hố Đen vũ trụ",
        "hook": "Nếu rơi vào hố đen, thời gian bên ngoài sẽ trôi qua hàng tỷ năm chỉ trong một chớp mắt.",
        "badge": "🔥 Triệu View",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "charon"
    },
    {
        "id": "space_2",
        "category": "space",
        "category_name": "🌌 Vũ Trụ & Khoa Học",
        "title": "Điều gì sẽ xảy ra nếu Mặt Trăng đột ngột biến mất?",
        "hook": "Thủy triều sụp đổ, trục Trái Đất chao đảo và một ngày của bạn sẽ chỉ còn vỏn vẹn 6 tiếng.",
        "badge": "🚀 Đang Hot",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "charon"
    },
    {
        "id": "space_3",
        "category": "space",
        "category_name": "🌌 Vũ Trụ & Khoa Học",
        "title": "Kính viễn vọng James Webb phát hiện thiên hà không thể tồn tại",
        "hook": "Những cấu trúc khổng lồ thách thức toàn bộ định luật vật lý thiên văn hiện đại.",
        "badge": "⭐ Khoa Học",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "aoede"
    },
    {
        "id": "space_4",
        "category": "space",
        "category_name": "🌌 Vũ Trụ & Khoa Học",
        "title": "Sự thật đáng sợ về Sao Neutron: Một thìa cà phê nặng bằng đỉnh Everest",
        "hook": "Vật chất đậm đặc nhất vũ trụ có thể xé toạc mọi phân tử trong nháy mắt.",
        "badge": "🔥 Khám Phá",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "charon"
    },

    # Đại dương & Thiên nhiên
    {
        "id": "ocean_1",
        "category": "ocean",
        "category_name": "🌊 Đại Dương & Thiên Nhiên",
        "title": "10 bí ẩn dưới đáy rãnh Mariana chưa từng được giải mã",
        "hook": "Nơi sâu nhất hành tinh ẩn chứa những âm thanh kỳ lạ mà khoa học chưa thể lý giải.",
        "badge": "🔥 Triệu View",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "charon"
    },
    {
        "id": "ocean_2",
        "category": "ocean",
        "category_name": "🌊 Đại Dương & Thiên Nhiên",
        "title": "Cá voi sát thủ Orca: Kẻ săn mồi thông minh nhất đại dương",
        "hook": "Chúng không phải cá voi, và trí tuệ xã hội của chúng phức tạp hơn con người tưởng.",
        "badge": "🚀 Đang Hot",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "fenrir"
    },
    {
        "id": "ocean_3",
        "category": "ocean",
        "category_name": "🌊 Đại Dương & Thiên Nhiên",
        "title": "Bí mật Quái vật Mực Khổng lồ Kraken dưới đáy biển sâu",
        "hook": "Đôi mắt to bằng chiếc đĩa và những chiếc xúc tua có thể xé toạc tàu bè.",
        "badge": "⭐ Kỳ Bí",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "charon"
    },

    # Lịch sử & Bí ẩn cổ đại
    {
        "id": "history_1",
        "category": "history",
        "category_name": "🏛️ Lịch Sử & Bí Ẩn",
        "title": "Bí mật đáng sợ bên trong Lăng mộ Tần Thủy Hoàng",
        "hook": "Dòng sông thủy ngân kịch độc và những bí mật hoàng đế muốn mang xuống mồ mãi mãi.",
        "badge": "🔥 Triệu View",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "charon"
    },
    {
        "id": "history_2",
        "category": "history",
        "category_name": "🏛️ Lịch Sử & Bí Ẩn",
        "title": "Đại Thư Viện Alexandria: Đám cháy thiêu rụi 1000 năm tri thức nhân loại",
        "hook": "Nhân loại có thể đã đặt chân lên Sao Hỏa từ thế kỷ 17 nếu nơi này không bị thiêu rụi.",
        "badge": "⭐ Lịch Sử",
        "image_model": "anime_media",
        "style": "Japanese Anime Makoto Shinkai",
        "voice": "aoede"
    },
    {
        "id": "history_3",
        "category": "history",
        "category_name": "🏛️ Lịch Sử & Bí Ẩn",
        "title": "Bí ẩn Kim Tự Tháp Giza: Cách người cổ đại nâng đá 50 tấn",
        "hook": "Độ chính xác vượt qua cả công nghệ xây dựng hiện đại của thế kỷ 21.",
        "badge": "🚀 Đang Hot",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "charon"
    },

    # Công nghệ & AI
    {
        "id": "tech_1",
        "category": "tech",
        "category_name": "🤖 Công Nghệ & AI",
        "title": "Kỷ nguyên Trí tuệ Nhân tạo Siêu phàm AGI: Điều gì chờ đợi nhân loại?",
        "hook": "Khi máy móc thông minh hơn toàn bộ bộ não nhân loại cộng lại, ai sẽ là kẻ làm chủ?",
        "badge": "🔥 Xu Hướng",
        "image_model": "anime_media",
        "style": "Cyberpunk Neon 2077",
        "voice": "puck"
    },
    {
        "id": "tech_2",
        "category": "tech",
        "category_name": "🤖 Công Nghệ & AI",
        "title": "Chip cấy não Neuralink: Đọc suy nghĩ hay khởi đầu của người lai máy?",
        "hook": "Bạn có thể điều khiển thế giới bằng ý nghĩ, nhưng liệu ý nghĩ của bạn có còn an toàn?",
        "badge": "🚀 Công Nghệ",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "kore"
    },
    {
        "id": "tech_3",
        "category": "tech",
        "category_name": "🤖 Công Nghệ & AI",
        "title": "Siêu máy tính lượng tử: Bẻ khóa toàn bộ mật mã thế giới trong 3 giây",
        "hook": "Công nghệ đe dọa sự tồn vong của toàn bộ hệ thống ngân hàng và internet toàn cầu.",
        "badge": "⭐ Đột Phá",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "fenrir"
    },

    # Tâm lý học & Đời sống
    {
        "id": "psychology_1",
        "category": "psychology",
        "category_name": "🧠 Tâm Lý & Đời Sống",
        "title": "Hiệu ứng Dunning-Kruger: Vì sao kẻ hiểu biết ít lại tự tin nhất?",
        "hook": "Càng biết ít, não bộ càng đánh lừa bạn rằng bạn đã thấu hiểu toàn bộ thế giới.",
        "badge": "🔥 Triệu View",
        "image_model": "anime_media",
        "style": "Japanese Anime Makoto Shinkai",
        "voice": "kore"
    },
    {
        "id": "psychology_2",
        "category": "psychology",
        "category_name": "🧠 Tâm Lý & Đời Sống",
        "title": "Nghịch lý Fermi: Nếu vũ trụ bao la, tại sao người ngoài hành tinh vẫn im lặng?",
        "hook": "Một giả thuyết lạnh gáy: Những nền văn minh khác có thể đã tự hủy diệt hoặc đang lẩn trốn.",
        "badge": "⭐ Triết Lý",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "charon"
    },
    {
        "id": "psychology_3",
        "category": "psychology",
        "category_name": "🧠 Tâm Lý & Đời Sống",
        "title": "Hiện tượng Déjà Vu: Não bộ bị lỗi nhịp hay ký ức từ vũ trụ song song?",
        "hook": "Cảm giác quen thuộc kỳ lạ khi bạn chắc chắn rằng mình đã từng sống trong khoảnh khắc này.",
        "badge": "🚀 Tò Mò",
        "image_model": "real_media",
        "style": "Cinematic Documentary",
        "voice": "aoede"
    }
]

class TopicExplorerService:
    """Dịch vụ tìm kiếm và gợi ý chủ đề video hot trend bằng AI và cơ sở dữ liệu curated."""

    @staticmethod
    def get_curated_topics(keyword: Optional[str] = None, category: Optional[str] = "all") -> List[Dict[str, Any]]:
        results = CURATED_TOPICS
        if category and category != "all":
            results = [t for t in results if t.get("category") == category]
        
        if keyword and keyword.strip():
            kw = keyword.strip().lower()
            results = [
                t for t in results
                if kw in t["title"].lower() or kw in t["hook"].lower() or kw in t.get("category_name", "").lower()
            ]
        return results

    @staticmethod
    async def generate_ai_suggestions(
        keyword: Optional[str] = None,
        category: Optional[str] = "all",
        gemini_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Sử dụng Gemini AI để brainstorm những chủ đề video ngắn giật gân, cuốn hút người xem."""
        key = gemini_key or os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if not key:
            # Fallback nếu chưa có API key
            return TopicExplorerService.get_curated_topics(keyword, category)

        category_labels = {
            "space": "Khoa học, Vũ trụ, Thiên văn bí ẩn",
            "ocean": "Đại dương, Sinh vật biển lạ, Thiên nhiên hoang dã",
            "history": "Lịch sử, Khảo cổ, Nền văn minh cổ đại bí ẩn",
            "tech": "Công nghệ tương lai, Trí tuệ nhân tạo AI, Đột phá khoa học",
            "psychology": "Tâm lý học con người, Nghịch lý triết học, Đời sống sâu sắc",
            "all": "Tổng hợp xu hướng hot trend TikTok / Shorts giật gân"
        }
        chosen_cat = category_labels.get(category, "Khoa học, Khám phá bí ẩn, Xu hướng")
        kw_prompt = f"liên quan đến từ khóa '{keyword}'" if keyword and keyword.strip() else "những chủ đề giật gân, tò mò nhất"

        prompt = f"""Bạn là chuyên gia sáng tạo nội dung video ngắn triệu view (TikTok, YouTube Shorts, Facebook Reels).
Nhiệm vụ của bạn: Đề xuất 6 chủ đề video {kw_prompt} thuộc lĩnh vực: {chosen_cat}.
Mỗi chủ đề phải cực kỳ cuốn hút, kích thích tò mò cao (High Hook Rate, High Retention), phù hợp với thị hiếu người xem Việt Nam.

Trả về DUY NHẤT một mảng JSON với cấu trúc sau:
[
  {{
    "title": "Tiêu đề video giật gân, súc tích (dưới 15 từ)",
    "hook": "Câu mở đầu 3 giây đầu tiên gây sốc hoặc tò mò",
    "badge": "🔥 Đề Xuất AI",
    "category": "{category if category != 'all' else 'space'}",
    "category_name": "{chosen_cat}",
    "image_model": "real_media",
    "style": "Cinematic Documentary",
    "voice": "charon"
  }}
]
"""
        try:
            client = genai.Client(api_key=key)
            models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
            last_err = None
            response_text = ""
            for m in models:
                try:
                    res = client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.7,
                            response_mime_type="application/json"
                        )
                    )
                    if res and res.text:
                        response_text = res.text
                        break
                except Exception as ex:
                    last_err = ex
                    continue
            
            if not response_text:
                raise last_err or Exception("Không nhận được phản hồi từ AI")

            data = json.loads(response_text)
            if isinstance(data, dict) and "topics" in data:
                data = data["topics"]
            if isinstance(data, list) and len(data) > 0:
                for idx, item in enumerate(data):
                    item["id"] = f"ai_{idx}_{hash(item.get('title', '')) % 10000}"
                    if "badge" not in item:
                        item["badge"] = "✨ AI Hot Trend"
                return data
        except Exception as e:
            logger.warning(f"Lỗi khi gọi AI gợi ý chủ đề: {e}, chuyển sang danh mục tuyển chọn.")

        # Fallback an toàn về dữ liệu tuyển chọn
        return TopicExplorerService.get_curated_topics(keyword, category)
