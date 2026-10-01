import os
import json
import logging
import random
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from app.config import settings
from app.models.health_organs import HEALTH_ORGANS, detect_organ_from_topic

logger = logging.getLogger("TopicSuggester")

# Kho dữ liệu chủ đề Sức Khỏe 100% tuyển chọn kết hợp Bộ Phận Hoạt Hình 3D Pixar
CURATED_HEALTH_TOPICS: List[Dict[str, Any]] = [
    # 🫘 1. LÁ GAN & THẢI ĐỘC
    {
        "id": "liver_1",
        "category": "liver",
        "category_name": "🫘 Gan & Thải Độc",
        "organ_name": "Bác Gan Cần Mẫn",
        "title": "Điều gì thực sự xảy ra với Lá Gan khi bạn thức khuya sau 11h đêm?",
        "hook": "Lá gan của bạn đang âm thầm gào thét mỗi khi bạn cố lướt thêm một video nữa sau nửa đêm!",
        "badge": "🔥 Gan Kêu Cứu",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "namminh"
    },
    {
        "id": "liver_2",
        "category": "liver",
        "category_name": "🫘 Gan & Thải Độc",
        "organ_name": "Bác Gan Cần Mẫn",
        "title": "3 dấu hiệu báo động Lá Gan đang bị bủa vây bởi lớp mỡ dày đặc",
        "hook": "Nổi mụn lưng và hơi thở có mùi lạ không phải do nóng trong, mà là lá gan đang kêu cứu!",
        "badge": "⚠️ Cảnh Báo",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "namminh"
    },
    {
        "id": "liver_3",
        "category": "liver",
        "category_name": "🫘 Gan & Thải Độc",
        "organ_name": "Bác Gan Cần Mẫn",
        "title": "Uống 1 ly nước ấm ngay khi ngủ dậy: Món quà hồi sinh lá gan 0 đồng",
        "hook": "Chỉ một hành động 10 giây này giúp lá gan tống sạch toàn bộ cặn bã tích tụ suốt đêm.",
        "badge": "⭐ Sống Khỏe",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "kore"
    },

    # 🧠 2. NÃO BỘ & GIẤC NGỦ
    {
        "id": "brain_1",
        "category": "brain",
        "category_name": "🧠 Não Bộ & Giấc Ngủ",
        "organ_name": "Bé Não Thông Thái",
        "title": "Não bộ tự 'ăn' chính các tế bào của nó ra sao nếu bạn mất ngủ 3 đêm?",
        "hook": "Khi bạn không ngủ, các tế bào dọn rác trong não sẽ nhầm lẫn và dọn luôn cả nơron thần kinh của bạn!",
        "badge": "🧠 Sốc Não",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "puck"
    },
    {
        "id": "brain_2",
        "category": "brain",
        "category_name": "🧠 Não Bộ & Giấc Ngủ",
        "organ_name": "Bé Não Thông Thái",
        "title": "Cái bẫy Dopamine: Vì sao ngón tay bạn không thể dừng lướt TikTok?",
        "hook": "Bộ não của bạn đang bị các thuật toán video ngắn bỏ bùa bằng những phát nổ Dopamine rẻ tiền!",
        "badge": "📱 Cai Nghiện",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "namminh"
    },
    {
        "id": "brain_3",
        "category": "brain",
        "category_name": "🧠 Não Bộ & Giấc Ngủ",
        "organ_name": "Bé Não Thông Thái",
        "title": "Hiện tượng Sương Mù Não: Vì sao người trẻ ngày càng hay quên?",
        "hook": "Bộ não của bạn không hề lão hóa, nó chỉ đang bị nghẹt thở vì quá tải thông tin rác!",
        "badge": "⚡ Tỉnh Táo",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "kore"
    },

    # 🧃 3. DẠ DÀY & TIÊU HÓA
    {
        "id": "stomach_1",
        "category": "stomach",
        "category_name": "🧃 Dạ Dày & Tiêu Hóa",
        "organ_name": "Bé Dạ Dày Nhạy Cảm",
        "title": "Bỏ bữa sáng: Dạ Dày buộc phải tự tiết axit tiêu hóa chính niêm mạc của nó",
        "hook": "Chiếc dạ dày trống rỗng lúc 8 giờ sáng giống như một biển axit sôi sục không có thức ăn để xử lý!",
        "badge": "⚠️ Đau Dạ Dày",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "puck"
    },
    {
        "id": "stomach_2",
        "category": "stomach",
        "category_name": "🧃 Dạ Dày & Tiêu Hóa",
        "organ_name": "Bé Dạ Dày Nhạy Cảm",
        "title": "Uống nước đá khi đang đói bụng: Cơn co thắt kinh hoàng của dạ dày",
        "hook": "Nhiệt độ đóng băng đột ngột khiến các mạch máu dạ dày co rúm lại và ngừng tiêu hóa thức ăn!",
        "badge": "❄️ Nước Đá",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "namminh"
    },
    {
        "id": "stomach_3",
        "category": "stomach",
        "category_name": "🧃 Dạ Dày & Tiêu Hóa",
        "organ_name": "Bé Dạ Dày Nhạy Cảm",
        "title": "Trào ngược dạ dày: Dòng axit đang âm thầm ăn mòn thực quản của bạn ra sao?",
        "hook": "Cảm giác nghẹn ở cổ họng không phải viêm họng, mà là tiếng gào thét của chiếc van dạ dày bị hở!",
        "badge": "🔥 Trào Ngược",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "kore"
    },

    # 🫀 4. TIM MẠCH & HUYẾT ÁP
    {
        "id": "heart_1",
        "category": "heart",
        "category_name": "🫀 Tim Mạch & Huyết Áp",
        "organ_name": "Chiến Binh Trái Tim",
        "title": "Trái tim bạn đập nhanh gấp đôi khi uống cốc cà phê thứ hai trong ngày?",
        "hook": "Mỗi ngày trái tim đập hơn 100.000 nhịp, và bạn đang bắt nó chạy marathon khi nhồi nhét caffeine!",
        "badge": "💓 Tim Khỏe",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "namminh"
    },
    {
        "id": "heart_2",
        "category": "heart",
        "category_name": "🫀 Tim Mạch & Huyết Áp",
        "organ_name": "Chiến Binh Trái Tim",
        "title": "Ngồi một chỗ quá 3 tiếng: Cục máu đông hình thành thế nào ở bắp chân?",
        "hook": "Kẻ giết người thầm lặng mang tên 'huyết khối' đang âm thầm bò ngược về tim của bạn ngay lúc này.",
        "badge": "🚨 Đột Quỵ",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "puck"
    },

    # 💧 5. THẬN & NƯỚC UỐNG
    {
        "id": "kidneys_1",
        "category": "kidneys",
        "category_name": "💧 Thận & Nước Uống",
        "organ_name": "Anh Em Song Sinh Thận",
        "title": "Thói quen nhịn tiểu: Điều kinh hoàng gì đang xảy ra bên trong quả thận?",
        "hook": "Dòng nước tiểu trào ngược mang theo hàng triệu vi khuẩn đang tàn phá bể thận từng giây một!",
        "badge": "⚠️ Đừng Nhịn Tiểu",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "kore"
    },
    {
        "id": "kidneys_2",
        "category": "kidneys",
        "category_name": "💧 Thận & Nước Uống",
        "organ_name": "Anh Em Song Sinh Thận",
        "title": "Một ngày lười uống nước: Hai quả thận biến thành chiếc máy nghiền canxi",
        "hook": "Những viên sỏi thận gai góc không tự nhiên sinh ra, nó là cái giá của việc bạn quên uống nước lọc!",
        "badge": "💧 Uống Nước Đi",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "namminh"
    },

    # 🫁 6. PHỔI & HÔ HẤP
    {
        "id": "lungs_1",
        "category": "lungs",
        "category_name": "🫁 Phổi & Hô Hấp",
        "organ_name": "Bé Phổi Trong Lành",
        "title": "Bụi mịn PM2.5 đi thẳng vào máu và phá hủy lá phổi mỏng manh ra sao?",
        "hook": "Khẩu trang thông thường hoàn toàn vô dụng trước những hạt bụi siêu vi đang găm chặt vào phế nang!",
        "badge": "🫁 Bụi Mịn",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "kore"
    },

    # 🦠 7. ĐƯỜNG RUỘT & HỆ VI SINH
    {
        "id": "gut_1",
        "category": "gut",
        "category_name": "🦠 Đường Ruột & Lợi Khuẩn",
        "organ_name": "Vương Quốc Đường Ruột",
        "title": "Đường ruột là bộ não thứ hai: Tâm trạng của bạn do vi khuẩn điều khiển?",
        "hook": "Bạn bỗng dưng cáu gắt và thèm ăn đồ ngọt không phải do tâm trạng, mà là đám vi khuẩn xấu đang biểu tình!",
        "badge": "🦠 Lợi Khuẩn",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "puck"
    },

    # 👁️ 8. ĐÔI MẮT & ÁNH SÁNG XANH
    {
        "id": "eyes_1",
        "category": "eyes",
        "category_name": "👁️ Mắt & Màn Hình",
        "organ_name": "Bé Mắt Tinh Anh",
        "title": "Tắt đèn bấm điện thoại trong đêm: Võng mạc bị nung nóng như dưới kính lúp",
        "hook": "Ánh sáng xanh phát ra từ điện thoại trong phòng tối đang hủy diệt tế bào thị giác nhanh gấp 5 lần!",
        "badge": "📱 Bật Đèn Lên",
        "image_model": "auto",
        "style": "3D Pixar Animation",
        "voice": "namminh"
    }
]

class TopicExplorerService:
    """Service đề xuất chủ đề Sức Khỏe chuyên sâu và Bộ Phận Cơ Thể Hoạt Hình 3D Pixar."""

    @staticmethod
    def get_curated_topics(keyword: Optional[str] = None, category: Optional[str] = "all") -> List[Dict[str, Any]]:
        topics = CURATED_HEALTH_TOPICS
        if category and category != "all":
            topics = [t for t in topics if t.get("category") == category]
        if keyword:
            kw = keyword.lower().strip()
            topics = [
                t for t in topics
                if kw in t["title"].lower() or kw in t["hook"].lower() or kw in t.get("organ_name", "").lower()
            ]
        return topics

    @staticmethod
    async def generate_ai_suggestions(
        keyword: Optional[str] = None,
        category: Optional[str] = "all",
        brain: str = "auto",
        gemini_key: Optional[str] = None,
        openai_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        g_key = gemini_key or os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        organ_info = HEALTH_ORGANS.get(category, HEALTH_ORGANS["liver"]) if category != "all" else None
        organ_focus = f"Tập trung đặc biệt vào bộ phận: {organ_info.organ_name} ({organ_info.name})" if organ_info else "Bao quát các bộ phận: Gan, Não, Dạ Dày, Tim, Thận, Phổi, Ruột, Mắt"

        prompt = f"""Bạn là Bác Sĩ Hoạt Hình & Giám Đốc Nội Dung Kênh Sức Khỏe Triệu View (phong cách Kurzgesagt / Pixar 3D Cells at Work).
Hãy sáng tạo 4 chủ đề video ngắn hoạt hình tiếng Việt cực kỳ lôi cuốn, giật gân, chạm đúng nỗi sợ và thói quen hàng ngày của mọi người.
Lĩnh vực: SỨC KHỎE CƠ THỂ CON NGƯỜI & BỘ PHẬN HOẠT HÌNH DẪN CHUYỆN.
{organ_focus}
Từ khóa gợi ý: {keyword or 'thói quen sức khỏe hàng ngày'}

Yêu cầu mỗi chủ đề:
1. `title`: Tiêu đề giật gân, dưới 16 từ.
2. `hook`: Câu mở màn 3 giây gây sốc khiến người xem giật mình kiểm tra cơ thể.
3. `category`: Một trong các mã bộ phận: 'liver', 'brain', 'stomach', 'heart', 'kidneys', 'lungs', 'gut', 'eyes'.
4. `organ_name`: Tên bộ phận nhân cách hóa (ví dụ: 'Bác Gan Cần Mẫn', 'Bé Não Thông Thái', 'Bé Dạ Dày Nhạy Cảm'...).
5. `badge`: Huy hiệu (ví dụ: '🔥 Gan Kêu Cứu', '⚠️ Đau Dạ Dày'...).

Trả về định dạng JSON mảng [{{...}}]:
[
  {{
    "title": "...",
    "hook": "...",
    "badge": "🔥 Hot",
    "category": "{category if category != 'all' else 'liver'}",
    "category_name": "{organ_info.category_title if organ_info else '🫘 Gan & Thải Độc'}",
    "organ_name": "{organ_info.name if organ_info else 'Bác Gan Cần Mẫn'}",
    "image_model": "auto",
    "style": "3D Pixar Animation",
    "voice": "namminh"
  }}
]
"""
        if g_key:
            try:
                client = genai.Client(api_key=g_key)
                res = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        response_mime_type="application/json"
                    )
                )
                if res and res.text:
                    data = json.loads(res.text)
                    if isinstance(data, dict) and "topics" in data:
                        data = data["topics"]
                    if isinstance(data, list) and len(data) > 0:
                        for idx, item in enumerate(data):
                            item["id"] = f"ai_health_{idx}_{random.randint(1000, 9999)}"
                        return data
            except Exception as e:
                logger.warning(f"Gemini Brain Health error: {e}")

        return TopicExplorerService.get_curated_topics(keyword, category)

    @staticmethod
    async def generate_single_live_trend(
        category: Optional[str] = "all",
        gemini_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tạo nhanh 1 chủ đề sức khỏe hoạt hình siêu hot."""
        g_key = gemini_key or os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        all_topics = CURATED_HEALTH_TOPICS
        if category and category != "all":
            filtered = [t for t in all_topics if t.get("category") == category]
            if filtered:
                all_topics = filtered
        selected = random.choice(all_topics)

        # Nếu có Gemini, viết lại cho độc lạ hơn
        if g_key:
            try:
                client = genai.Client(api_key=g_key)
                p = f"""Hãy làm mới chủ đề sức khỏe hoạt hình sau thành 1 tiêu đề và câu hook triệu view TikTok cực kỳ giật gân:
Chủ đề gốc: {selected['title']}
Bộ phận hoạt hình: {selected['organ_name']}
Trả về JSON: {{"title": "...", "hook": "..."}}"""
                res = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=p,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                if res and res.text:
                    d = json.loads(res.text)
                    return {
                        **selected,
                        "title": d.get("title", selected["title"]),
                        "hook": d.get("hook", selected["hook"]),
                        "badge": "⚡ AI Live Sức Khỏe"
                    }
            except Exception:
                pass

        return selected
