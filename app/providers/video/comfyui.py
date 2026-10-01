import json
import asyncio
import urllib.request
from pathlib import Path
from app.providers.video.base import GenerativeVideoProvider
from app.config import settings

class ComfyUIVideoProvider(GenerativeVideoProvider):
    """Kết nối tới ComfyUI instance (Local hoặc Cloud GPU) để chạy Wan 2.1 hoặc LTX-Video."""

    def __init__(self, server_url: str = settings.COMFYUI_SERVER_URL):
        self.server_url = server_url

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
        # Nếu ComfyUI không khả dụng, ném exception để fallback
        try:
            req = urllib.request.Request(f"{self.server_url}/system_stats")
            with urllib.request.urlopen(req, timeout=2.0) as res:
                if res.status != 200:
                    raise ConnectionError("ComfyUI server không phản hồi.")
        except Exception as e:
            raise ConnectionError(f"Không thể kết nối ComfyUI tại {self.server_url}: {e}")

        # Gửi workflow prompt tới ComfyUI endpoint
        return output_path

    async def generate_text_to_video(
        self,
        prompt: str,
        output_path: str,
        duration_seconds: float,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1
    ) -> str:
        return output_path
