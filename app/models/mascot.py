from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class MascotProfile(BaseModel):
    id: str
    name: str
    role_title: str
    category: str
    persona_prompt: str
    visual_anchor: str
    recommended_voice: str = "namminh"
    style_suffix: str = (
        "cute 3D Pixar Disney animated movie style, vibrant warm lighting, "
        "expressive character, high quality 3D render, octane render"
    )

def get_mascot(mascot_id: Optional[str] = None, topic: Optional[str] = None) -> MascotProfile:
    """Lấy cấu hình linh vật bộ phận cơ thể hoạt hình 3D Pixar theo ID hoặc phân tích từ chủ đề."""
    from app.models.health_organs import HEALTH_ORGANS, detect_organ_from_topic

    m_id = (mascot_id or "").strip().lower()
    
    # 1. Nếu chỉ định cụ thể một bộ phận cơ thể
    if m_id in HEALTH_ORGANS:
        organ = HEALTH_ORGANS[m_id]
        return MascotProfile(
            id=organ.id,
            name=organ.name,
            role_title=organ.category_title,
            category="health",
            persona_prompt=organ.persona_prompt,
            visual_anchor=organ.visual_anchor,
            recommended_voice="namminh" if organ.id in ["liver", "heart"] else "kore",
            style_suffix=organ.style_suffix
        )

    # 2. Nếu có topic, tự động nhận diện bộ phận tương ứng
    if topic:
        organ = detect_organ_from_topic(topic)
        return MascotProfile(
            id=organ.id,
            name=organ.name,
            role_title=organ.category_title,
            category="health",
            persona_prompt=organ.persona_prompt,
            visual_anchor=organ.visual_anchor,
            recommended_voice="namminh" if organ.id in ["liver", "heart"] else "kore",
            style_suffix=organ.style_suffix
        )

    # 3. Mặc định: Bác Gan Cần Mẫn
    default_organ = HEALTH_ORGANS["liver"]
    return MascotProfile(
        id=default_organ.id,
        name=default_organ.name,
        role_title=default_organ.category_title,
        category="health",
        persona_prompt=default_organ.persona_prompt,
        visual_anchor=default_organ.visual_anchor,
        recommended_voice="namminh",
        style_suffix=default_organ.style_suffix
    )
