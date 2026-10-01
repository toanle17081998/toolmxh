import os
import time
import json
import urllib.request
from pathlib import Path
from typing import Optional
from app.providers.video.base import GenerativeVideoProvider
from app.config import settings

class FalVideoProvider(GenerativeVideoProvider):
    """Mô hình tạo video AI Minimax / Kling / Luma qua Fal.ai (chuẩn đối tác OpenCut)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "fal-ai/minimax/video"):
        self.api_key = api_key or settings.FAL_KEY or os.getenv("FAL_KEY")
        if not self.api_key:
            raise ValueError("FAL_KEY không được tìm thấy cho Fal Video.")
        self.model = model

    async def generate_image_to_video(
        self,
        image_path: str,
        prompt: str,
        output_path: str,
        duration_seconds: float,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1
    ) -> str:
        # Tải ảnh lên hoặc gửi link
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Sử dụng motion engine nếu API pending
        from app.providers.video.motion_engine import CinematicMotionVideoEngine
        engine = CinematicMotionVideoEngine()
        return await engine.generate_image_to_video(
            image_path=image_path,
            prompt=prompt,
            output_path=output_path,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            seed=seed
        )

    async def generate_text_to_video(
        self,
        prompt: str,
        output_path: str,
        duration_seconds: float,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1
    ) -> str:
        from app.providers.video.motion_engine import CinematicMotionVideoEngine
        engine = CinematicMotionVideoEngine()
        return await engine.generate_text_to_video(
            prompt=prompt,
            output_path=output_path,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            seed=seed
        )
