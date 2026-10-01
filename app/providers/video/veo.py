import os
import time
import urllib.request
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from app.providers.video.base import GenerativeVideoProvider
from app.config import settings

import logging
from app.providers.video.motion_engine import CinematicMotionVideoEngine

logger = logging.getLogger(__name__)

class GoogleVeoVideoProvider(GenerativeVideoProvider):
    """Mô hình Generative Video mới nhất và mạnh mẽ nhất của Google: Veo 3.1 (veo-3.1-generate-preview)."""

    supports_health_animation = True

    async def generate_health_video(self, **kwargs):
        import asyncio
        return await asyncio.to_thread(lambda: asyncio.run(self.generate_image_to_video(**kwargs, allow_fallback=False)))

    def __init__(self, api_key: Optional[str] = None, model: str = "veo-3.1-generate-preview"):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY không được tìm thấy để sử dụng Google Veo.")
        self.client = genai.Client(api_key=self.api_key)
        self.model = model
        self.motion_engine = CinematicMotionVideoEngine()

    async def generate_image_to_video(
        self,
        image_path: str,
        prompt: str,
        output_path: str,
        duration_seconds: float,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1,
        allow_fallback: bool = True
    ) -> str:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            candidates = [self.model, "veo-3.1-generate-preview", "veo-3.1-fast-generate-preview"]
            chosen_op = None
            last_err = None
            for m in candidates:
                try:
                    chosen_op = self.client.models.generate_videos(
                        model=m,
                        prompt=prompt,
                        image=types.Image(image_bytes=image_bytes, mime_type="image/png"),
                        config=types.GenerateVideosConfig(
                            aspect_ratio="9:16" if height > width else "16:9",
                            person_generation="ALLOW_ADULT",
                            duration_seconds=(8 if duration_seconds > 6 else 6 if duration_seconds > 4 else 4) if not allow_fallback else int(min(8, max(5, duration_seconds))),
                            generate_audio=False if not allow_fallback else None
                        )
                    )
                    if chosen_op:
                        break
                except Exception as e:
                    last_err = e
                    continue

            if not chosen_op:
                raise last_err or RuntimeError("Không thể gọi Veo model.")

            deadline = time.monotonic() + 600
            while not chosen_op.done:
                if time.monotonic() > deadline:
                    raise TimeoutError("Veo operation did not complete within 10 minutes")
                time.sleep(5)
                chosen_op = self.client.operations.get(chosen_op)

            result = chosen_op.result or chosen_op.response
            if not result or not result.generated_videos:
                raise RuntimeError("Veo returned no generated video")
            generated_video = result.generated_videos[0].video
            video_bytes = generated_video.video_bytes
            if not video_bytes:
                video_bytes = self.client.files.download(file=generated_video)
            if not video_bytes:
                raise RuntimeError("Veo returned no downloadable video data")
            with open(out_path, "wb") as f:
                f.write(video_bytes)
            return str(out_path)

        except Exception as e:
            if not allow_fallback:
                raise RuntimeError(f"Veo health animation failed ({type(e).__name__}); no still-image or stock fallback permitted") from e
            logger.warning(f"Google Veo ({self.model}) gặp lỗi hoặc hạn mức quota ({e}), chuyển sang Lanczos Cinematic Motion Engine...")
            return await self.motion_engine.generate_image_to_video(
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
        return await self.motion_engine.generate_text_to_video(
            prompt=prompt,
            output_path=output_path,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            seed=seed
        )
