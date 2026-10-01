import os
import time
import urllib.request
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from app.providers.video.base import GenerativeVideoProvider
from app.config import settings

class GoogleVeoVideoProvider(GenerativeVideoProvider):
    """Mô hình Generative Video mới nhất và mạnh mẽ nhất của Google: Veo 2 (veo-2.0-generate-001)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY không được tìm thấy để sử dụng Google Veo.")
        self.client = genai.Client(api_key=self.api_key)

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
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Đọc ảnh tham chiếu
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        operation = self.client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt=prompt,
            image=types.Image(image_bytes=image_bytes, mime_type="image/png"),
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16" if height > width else "16:9",
                person_generation="ALLOW_ADULT",
                duration_seconds=int(min(8, max(5, duration_seconds)))
            )
        )

        # Chờ tác vụ hoàn thành (Polled operation)
        while not operation.done:
            time.sleep(5)
            operation = self.client.operations.get(operation)

        video_bytes = operation.result.generated_videos[0].video.video_bytes
        with open(out_path, "wb") as f:
            f.write(video_bytes)

        return str(out_path)

    async def generate_text_to_video(
        self,
        prompt: str,
        output_path: str,
        duration_seconds: float,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1
    ) -> str:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        operation = self.client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16" if height > width else "16:9",
                person_generation="ALLOW_ADULT",
                duration_seconds=int(min(8, max(5, duration_seconds)))
            )
        )
        while not operation.done:
            time.sleep(5)
            operation = self.client.operations.get(operation)

        video_bytes = operation.result.generated_videos[0].video.video_bytes
        with open(out_path, "wb") as f:
            f.write(video_bytes)

        return str(out_path)
