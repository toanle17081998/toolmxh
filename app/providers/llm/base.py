from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.models.script import StructuredScript
from app.models.storyboard import Storyboard, VisualStyleBible

class LLMProvider(ABC):
    """Lớp trừu tượng cho Content Brain (Gemini, OpenAI, Local)."""

    @abstractmethod
    async def research_topic(self, topic: str) -> Dict[str, Any]:
        """Nghiên cứu góc nhìn hấp dẫn, sự thật giật gân về chủ đề."""
        pass

    @abstractmethod
    async def generate_script(
        self,
        topic: str,
        target_duration: int = 60,
        platform: str = "tiktok",
        language: str = "vi",
        mascot_id: Optional[str] = "dr_bear"
    ) -> StructuredScript:
        """Sinh kịch bản tiếng Việt có cấu trúc chặt chẽ gồm hook và danh sách cảnh có linh vật dẫn chuyện."""
        pass

    @abstractmethod
    async def generate_storyboard(
        self,
        script: StructuredScript,
        visual_bible: Optional[VisualStyleBible] = None,
        mascot_id: Optional[str] = "dr_bear"
    ) -> Storyboard:
        """Phân rã kịch bản thành danh sách shot quay điện ảnh chi tiết có sự hiện diện của linh vật."""
        pass

    @abstractmethod
    async def generate_metadata(
        self,
        topic: str,
        script: StructuredScript
    ) -> Dict[str, Any]:
        """Tạo tiêu đề, mô tả, hashtag cho TikTok, YouTube Shorts, Facebook Reels."""
        pass
