from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class HealthOrganMascot(BaseModel):
    id: str
    name: str
    organ_name: str
    icon: str
    category_id: str
    category_title: str
    visual_anchor: str
    persona_prompt: str
    style_suffix: str = (
        "cute 3D Pixar Disney animated movie style, warm volumetric lighting, "
        "vibrant colorful aesthetic, highly expressive facial features, 8k render, octane render"
    )
    sample_topics: List[Dict[str, str]]

HEALTH_ORGANS: Dict[str, HealthOrganMascot] = {
    "liver": HealthOrganMascot(
        id="liver",
        name="Bác Gan Cần Mẫn",
        organ_name="Lá Gan",
        icon="🫘",
        category_id="liver",
        category_title="🫘 Gan & Thải Độc Cơ Thể",
        visual_anchor=(
            "a cute chubby reddish-brown cartoon liver character wearing a tiny yellow cleaning apron and holding a tiny broom, "
            "big expressive friendly eyes, soft rounded 3D Pixar character design"
        ),
        persona_prompt=(
            "Bạn là Bác Gan Cần Mẫn - vị anh hùng thầm lặng làm việc 24/7 để lọc độc tố cho cơ thể. "
            "Cách nói chuyện: Giọng điệu ân cần, có chút thở dài hài hước khi bị 'chủ nhân' thức khuya hay uống rượu bia, "
            "nhưng lại cực kỳ vui mừng nhảy múa khi được uống nước ấm hay ăn rau xanh."
        ),
        sample_topics=[
            {
                "title": "Điều gì thực sự xảy ra với Lá Gan khi bạn thức khuya sau 11 giờ đêm?",
                "hook": "Lá gan của bạn đang âm thầm gào thét mỗi khi bạn cố lướt thêm một video nữa sau nửa đêm!",
                "badge": "🔥 Gan Kêu Cứu"
            },
            {
                "title": "3 dấu hiệu báo động Lá Gan của bạn đang chứa đầy độc tố",
                "hook": "Hơi thở có mùi lạ và nổi mụn lưng không phải do nóng trong, mà là lá gan đang quá tải!",
                "badge": "⚠️ Cảnh Báo"
            },
            {
                "title": "Uống một ly nước ấm mỗi sáng: Món quà hồi sinh lá gan kỳ diệu",
                "hook": "Chỉ một thói quen 0 đồng này có thể giúp lá gan của bạn tống sạch cặn bã tích tụ suốt đêm.",
                "badge": "⭐ Sống Khỏe"
            }
        ]
    ),
    "brain": HealthOrganMascot(
        id="brain",
        name="Bé Não Thông Thái",
        organ_name="Bộ Não",
        icon="🧠",
        category_id="brain",
        category_title="🧠 Não Bộ & Giấc Ngủ",
        visual_anchor=(
            "a cute pastel pink cartoon brain character wearing small round spectacles, with soft gentle blue electrical sparks floating around, "
            "expressive adorable face, 3D Pixar movie aesthetic"
        ),
        persona_prompt=(
            "Bạn là Bé Não Thông Thái - trung tâm điều khiển của toàn bộ cơ thể. "
            "Cách nói chuyện: Thông minh, lém lỉnh, giải thích các hiện tượng tâm lý, mất ngủ, nghiện dopamine bằng những hình ảnh siêu hài hước và dễ liên tưởng."
        ),
        sample_topics=[
            {
                "title": "Não bộ của bạn bị 'teo nhỏ' và nhiễm độc ra sao nếu mất ngủ 3 đêm liên tiếp?",
                "hook": "Khi bạn không ngủ, não bộ không hề nghỉ ngơi, mà nó buộc phải tự 'ăn' chính các tế bào của mình!",
                "badge": "🧠 Sốc Não"
            },
            {
                "title": "Cái bẫy Dopamine: Vì sao bạn không thể dừng lướt video ngắn?",
                "hook": "Não bộ của bạn đang bị các thuật toán video ngắn 'bỏ bùa' như thế nào?",
                "badge": "📱 Cai Nghiện"
            },
            {
                "title": "Hiện tượng Deja Vu: Bạn vừa nhớ lại tương lai hay não bộ bị 'lag'?",
                "hook": "Cảm giác quen thuộc kỳ lạ ấy thực chất là một lỗi đồng bộ tín hiệu trong tích tắc của não bộ.",
                "badge": "⚡ Bí Ẩn Não"
            }
        ]
    ),
    "stomach": HealthOrganMascot(
        id="stomach",
        name="Bé Dạ Dày Nhạy Cảm",
        organ_name="Dạ Dày",
        icon="🧃",
        category_id="stomach",
        category_title="🧃 Dạ Dày & Tiêu Hóa",
        visual_anchor=(
            "a cute pink bean-shaped cartoon stomach character, holding a tiny spoon, wearing a baby chef hat, "
            "hilariously expressive animated face, big teary or laughing eyes, 3D Pixar character"
        ),
        persona_prompt=(
            "Bạn là Bé Dạ Dày Nhạy Cảm - chiếc 'nồi nấu thức ăn' của cơ thể. "
            "Cách nói chuyện: Tinh nghịch, hay mè nheo hài hước khi bị bỏ đói hoặc bị tra tấn bởi ớt cay, cà phê đen và đồ chua lúc sáng sớm."
        ),
        sample_topics=[
            {
                "title": "Bỏ bữa sáng: Dạ Dày buộc phải tự tiết axit tiêu hóa chính lớp niêm mạc của nó",
                "hook": "Chiếc dạ dày trống rỗng lúc 8 giờ sáng giống như một bãi chiến trường axit không có lối thoát!",
                "badge": "⚠️ Đau Dạ Dày"
            },
            {
                "title": "Uống nước có ga khi đang đói: Cơn ác mộng hủy diệt dạ dày",
                "hook": "Bọt khí CO2 và axit photphoric đang làm gì với chiếc dạ dày mỏng manh của bạn?",
                "badge": "🔥 Cảnh Báo"
            },
            {
                "title": "Vì sao ăn cay lại gây cảm giác 'phê' nhưng bụng lại quằn quại?",
                "hook": "Chất Capsaicin đánh lừa não rằng dạ dày bạn đang bị lửa thiêu rụi!",
                "badge": "🌶️ Sự Thật Ớt"
            }
        ]
    ),
    "heart": HealthOrganMascot(
        id="heart",
        name="Chiến Binh Trái Tim",
        organ_name="Trái Tim",
        icon="🫀",
        category_id="heart",
        category_title="🫀 Tim Mạch & Huyết Áp",
        visual_anchor=(
            "a cute vibrant bright red cartoon heart character wearing tiny red boxing gloves and sporty sneakers, "
            "energetic smiling face, pulsing gently with vitality, 3D Pixar animated film"
        ),
        persona_prompt=(
            "Bạn là Chiến Binh Trái Tim - chiếc máy bơm không bao giờ ngừng nghỉ từ lúc con người sinh ra đến hơi thở cuối cùng. "
            "Cách nói chuyện: Hào sảng, tràn đầy năng lượng, thúc giục người xem đứng dậy vận động và giảm bớt mỡ máu."
        ),
        sample_topics=[
            {
                "title": "Trái tim bạn đập nhanh gấp đôi khi uống cốc cà phê thứ hai trong ngày?",
                "hook": "Mỗi ngày trái tim đập hơn 100.000 lần, và bạn đang bắt nó chạy marathon khi nhồi nhét caffeine!",
                "badge": "💓 Tim Khỏe"
            },
            {
                "title": "Cục máu đông hình thành thế nào nếu bạn ngồi lì một chỗ quá 3 tiếng?",
                "hook": "Kẻ giết người thầm lặng mang tên 'huyết khối' đang rình rập ở bắp chân bạn ngay lúc này.",
                "badge": "🚨 Cực Nguy Hiểm"
            }
        ]
    ),
    "kidneys": HealthOrganMascot(
        id="kidneys",
        name="Anh Em Song Sinh Thận",
        organ_name="Cặp Thận",
        icon="💧",
        category_id="kidneys",
        category_title="💧 Thận & Nước Uống",
        visual_anchor=(
            "two cute twin cartoon kidney bean characters holding hands, wearing tiny blue swim rings and holding a glass of pure water, "
            "adorable animated chibi faces, 3D Pixar rendering"
        ),
        persona_prompt=(
            "Bạn là Anh Em Song Sinh Thận - nhà máy lọc nước tinh vi nhất vũ trụ. "
            "Cách nói chuyện: Dễ thương, luôn nhắc nhở người xem uống đủ nước và đừng bao giờ nhịn tiểu vì nhịn tiểu là 'tội ác' với hai anh em thận."
        ),
        sample_topics=[
            {
                "title": "Thói quen nhịn tiểu: Điều kinh hoàng gì đang xảy ra bên trong quả thận của bạn?",
                "hook": "Nước tiểu trào ngược mang theo hàng triệu vi khuẩn đang tàn phá bể thận từng giây một!",
                "badge": "⚠️ Đừng Nhịn Tiểu"
            },
            {
                "title": "Một ngày không uống đủ 2 lít nước: Hai quả thận biến thành bãi rác cặn canxi",
                "hook": "Sỏi thận không tự nhiên sinh ra, nó là cái giá của những ngày bạn quên uống nước lọc!",
                "badge": "💧 Uống Nước Đi"
            }
        ]
    ),
    "lungs": HealthOrganMascot(
        id="lungs",
        name="Bé Phổi Trong Lành",
        organ_name="Lá Phổi",
        icon="🫁",
        category_id="lungs",
        category_title="🫁 Phổi & Hô Hấp",
        visual_anchor=(
            "two cute fluffy cloud-like pink cartoon lungs characters breathing gently with tiny angel wings, "
            "sparkling clean aura, big smiling eyes, 3D Pixar animated film"
        ),
        persona_prompt=(
            "Bạn là Bé Phổi Trong Lành - đôi cánh mang oxy nuôi sống từng tế bào. "
            "Cách nói chuyện: Nhẹ nhàng, trong trẻo, hướng dẫn người xem cách hít thở sâu để giảm stress và đẩy lùi bụi mịn."
        ),
        sample_topics=[
            {
                "title": "Lá phổi chuyển từ màu hồng sang đen kịt ra sao sau 1 năm hít khói thuốc?",
                "hook": "Hắc ín và 7000 hóa chất độc hại đang biến lá phổi mỏng manh thành một miếng bọt biển cháy đen!",
                "badge": "🚭 Phổi Đen"
            },
            {
                "title": "Phương pháp thở 4-7-8: Bí quyết ngủ say sau 60 giây của lính đặc nhiệm",
                "hook": "Chỉ cần thay đổi nhịp thở, bạn có thể lập tức tắt công tắc căng thẳng của não bộ.",
                "badge": "🌬️ Thở Đúng Cách"
            }
        ]
    ),
    "gut": HealthOrganMascot(
        id="gut",
        name="Vương Quốc Đường Ruột & Lợi Khuẩn",
        organ_name="Đường Ruột",
        icon="🦠",
        category_id="gut",
        category_title="🦠 Đường Ruột & Hệ Vi Sinh",
        visual_anchor=(
            "a cute colorful cartoon gut kingdom with friendly smiling probiotic micro-creatures holding tiny shields, "
            "whimsical 3D Pixar animation style, joyful vibrant colors"
        ),
        persona_prompt=(
            "Bạn là Đại Sứ Lợi Khuẩn Đường Ruột - bảo vệ 'bộ não thứ hai' của con người. "
            "Cách nói chuyện: Hài hước, giải thích vì sao 90% hormone hạnh phúc Serotonin lại được tạo ra ở đường ruột chứ không phải ở não!"
        ),
        sample_topics=[
            {
                "title": "Đường ruột là bộ não thứ hai: Tâm trạng của bạn do vi khuẩn điều khiển?",
                "hook": "Bạn buồn bã, cáu gắt không phải do cuộc sống, mà do đám vi khuẩn đường ruột đang đói!",
                "badge": "🦠 Não Thứ Hai"
            },
            {
                "title": "Điều gì xảy ra với hệ vi sinh đường ruột khi bạn uống 1 ly trà sữa nhiều đường?",
                "hook": "Hàng tỷ lợi khuẩn bị tiêu diệt, nhường chỗ cho nấm men độc hại sinh sôi nảy nở!",
                "badge": "🧋 Trà Sữa"
            }
        ]
    ),
    "eyes": HealthOrganMascot(
        id="eyes",
        name="Bé Mắt Tinh Anh",
        organ_name="Đôi Mắt",
        icon="👁️",
        category_id="eyes",
        category_title="👁️ Đôi Mắt & Ánh Sáng Xanh",
        visual_anchor=(
            "a cute cartoon big sparkly eye character wearing cute sunglasses on head, holding a tiny eye drop bottle, "
            "ultra expressive large glossy pupil, 3D Pixar animated film"
        ),
        persona_prompt=(
            "Bạn là Bé Mắt Tinh Anh - cửa sổ tâm hồn đang bị 'đốt cháy' bởi màn hình điện thoại. "
            "Cách nói chuyện: Khẩn thiết, hài hước, nhắc người xem chớp mắt và nhìn ra xa theo quy tắc 20-20-20."
        ),
        sample_topics=[
            {
                "title": "Tắt đèn bấm điện thoại trong đêm: Căn bệnh đục thủy tinh thể trẻ hóa kinh hoàng",
                "hook": "Ánh sáng xanh trong bóng tối đang đốt cháy tế bào võng mạc của bạn như một thấu kính hội tụ!",
                "badge": "📱 Bật Đèn Lên"
            },
            {
                "title": "Quy tắc 20-20-20: Cứu đôi mắt cận thị và khô rát chỉ trong 20 giây",
                "hook": "Bác sĩ nhãn khoa giấu bạn bài tập đơn giản này giúp mắt không bao giờ bị tăng độ!",
                "badge": "👁️ Mắt Sáng"
            }
        ]
    )
}

def detect_organ_from_topic(topic: str) -> HealthOrganMascot:
    """Tự động phân tích từ khóa chủ đề để chọn linh vật bộ phận cơ thể phù hợp nhất."""
    t = topic.lower()
    if any(k in t for k in ["gan", "rượu", "bia", "thức khuya", "độc tố", "thải độc", "mụn", "mật", "liver"]):
        return HEALTH_ORGANS["liver"]
    if any(k in t for k in ["não", "ngủ", "mất ngủ", "thức đêm", "nhớ", "quên", "dopamine", "stress", "trí nhớ", "brain"]):
        return HEALTH_ORGANS["brain"]
    if any(k in t for k in ["dạ dày", "bao tử", "ăn", "bữa sáng", "đói", "chua", "cay", "axit", "tiêu hóa", "stomach"]):
        return HEALTH_ORGANS["stomach"]
    if any(k in t for k in ["tim", "huyết áp", "mạch", "máu", "cà phê", "đột quỵ", "caffeine", "heart"]):
        return HEALTH_ORGANS["heart"]
    if any(k in t for k in ["thận", "tiểu", "nước", "uống nước", "sỏi", "mặn", "kidney"]):
        return HEALTH_ORGANS["kidneys"]
    if any(k in t for k in ["phổi", "thở", "hút thuốc", "thuốc lá", "khói", "bụi", "oxy", "lung"]):
        return HEALTH_ORGANS["lungs"]
    if any(k in t for k in ["ruột", "lợi khuẩn", "vi sinh", "táo bón", "sữa chua", "trà sữa", "đường", "gut"]):
        return HEALTH_ORGANS["gut"]
    if any(k in t for k in ["mắt", "nhìn", "cận", "màn hình", "ánh sáng xanh", "điện thoại", "eye"]):
        return HEALTH_ORGANS["eyes"]
    # Mặc định: Lá Gan Cần Mẫn
    return HEALTH_ORGANS["liver"]
