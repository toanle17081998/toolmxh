from typing import List, Optional
from pydantic import BaseModel, Field

class SceneScript(BaseModel):
    id: int = Field(description="Số thứ tự cảnh (1, 2, 3...)")
    narration: str = Field(description="Lời thuyết minh tiếng Việt tự nhiên, lôi cuốn")
    visual: str = Field(description="Mô tả bối cảnh hình ảnh diễn biến trong cảnh")
    estimated_duration: float = Field(default=5.0, description="Thời lượng ước tính (giây)")
    camera_motion: str = Field(default="slow zoom in", description="Chuyển động máy quay (zoom in, pan left, orbit...)")
    transition: str = Field(default="cut", description="Hiệu ứng chuyển cảnh (cut, fade, dissolve)")
    sound_effect: Optional[str] = Field(default=None, description="Tên hiệu ứng âm thanh nếu có")

class StructuredScript(BaseModel):
    title: str = Field(description="Tiêu đề video giật tít, hấp dẫn")
    hook: str = Field(description="Câu mở đầu giật gân thu hút người xem trong 3s đầu")
    target_duration: int = Field(default=60, description="Tổng thời lượng video (giây)")
    language: str = Field(default="vi")
    scenes: List[SceneScript] = Field(description="Danh sách các cảnh phân rã của video")
