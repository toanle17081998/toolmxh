import os
import json
import logging
import asyncio
import urllib.request
from pathlib import Path
from typing import Optional

from app.providers.video.base import GenerativeVideoProvider
from app.config import settings

logger = logging.getLogger(__name__)

class WanVideoProvider(GenerativeVideoProvider):
    """
    Wan-Video (Wan2.1 / Wan2.2) Provider từ Alibaba Cloud / Wan-Video Team:
    Mô hình Video Diffusion SOTA hỗ trợ Text-to-Video (1.3B / 14B) và Image-to-Video (14B).
    Tích hợp qua Fal.ai, Replicate API, hoặc Local ComfyUI.
    """

    def __init__(
        self,
        model_size: str = "1.3b",  # "1.3b" hoặc "14b"
        fal_key: Optional[str] = None,
        replicate_token: Optional[str] = None
    ):
        self.model_size = model_size.lower()
        self.fal_key = fal_key or os.getenv("FAL_KEY") or settings.FAL_KEY
        self.replicate_token = replicate_token or os.getenv("REPLICATE_API_TOKEN") or settings.REPLICATE_API_TOKEN

    async def _download_video(self, url: str, output_path: str):
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        def _dl():
            proxy = os.getenv("HTTP_PROXY") or "http://172.16.120.13:3128"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with opener.open(req, timeout=120) as resp, open(out_p, "wb") as f:
                f.write(resp.read())
        await asyncio.to_thread(_dl)

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
        """Sinh video từ ảnh tham chiếu (Image-to-Video) bằng Wan2.1."""
        aspect_ratio = "9:16" if height >= width else "16:9"

        # 1. Thử qua Fal.ai nếu có FAL_KEY
        if self.fal_key:
            try:
                import fal_client
                os.environ["FAL_KEY"] = self.fal_key
                logger.info(f"Đang gọi Wan2.1 Image-to-Video qua Fal.ai cho prompt: '{prompt[:60]}...'")

                # Upload ảnh lên Fal storage
                image_url = await asyncio.to_thread(fal_client.upload_file, image_path)

                handler = await asyncio.to_thread(
                    fal_client.submit,
                    "fal-ai/wan/v2.1/i2v-14b",
                    arguments={
                        "image_url": image_url,
                        "prompt": prompt,
                        "aspect_ratio": aspect_ratio
                    }
                )
                result = await asyncio.to_thread(handler.get)
                video_url = result.get("video", {}).get("url")
                if video_url:
                    await self._download_video(video_url, output_path)
                    return output_path
            except Exception as e:
                logger.warning(f"Wan2.1 Fal.ai I2V lỗi: {e}")

        # 2. Thử qua Replicate nếu có REPLICATE_API_TOKEN
        if self.replicate_token:
            try:
                import replicate
                os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
                logger.info(f"Đang gọi Wan2.1 qua Replicate...")
                with open(image_path, "rb") as img_file:
                    output = await asyncio.to_thread(
                        replicate.run,
                        "wan-video/wan-2.1-i2v-480p",
                        input={
                            "image": img_file,
                            "prompt": prompt,
                            "aspect_ratio": aspect_ratio
                        }
                    )
                if output:
                    video_url = output if isinstance(output, str) else output[0]
                    await self._download_video(str(video_url), output_path)
                    return output_path
            except Exception as e:
                logger.warning(f"Wan2.1 Replicate I2V lỗi: {e}")

        # 3. Fallback sang Semantic Cinematic Motion Engine (100% bám sát ảnh AI theo kịch bản)
        from app.providers.video.semantic_engine import SemanticMotionVideoEngine
        engine = SemanticMotionVideoEngine()
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
        """Sinh video trực tiếp từ Prompt văn bản (Text-to-Video) bằng Wan2.1 / Wan2.2."""
        aspect_ratio = "9:16" if height >= width else "16:9"
        model_endpoint = "fal-ai/wan/v2.1/t2v-1.3b" if self.model_size == "1.3b" else "fal-ai/wan/v2.1/t2v-14b"

        # 1. Thử qua Fal.ai
        if self.fal_key:
            try:
                import fal_client
                os.environ["FAL_KEY"] = self.fal_key
                logger.info(f"Đang gọi Wan2.1 ({self.model_size}) T2V qua Fal.ai...")
                result = await asyncio.to_thread(
                    fal_client.subscribe,
                    model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "aspect_ratio": aspect_ratio
                    }
                )
                video_url = result.get("video", {}).get("url")
                if video_url:
                    await self._download_video(video_url, output_path)
                    return output_path
            except Exception as e:
                logger.warning(f"Wan2.1 Fal.ai T2V lỗi: {e}")

        # 2. Thử qua Replicate
        if self.replicate_token:
            try:
                import replicate
                os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
                logger.info(f"Đang gọi Wan2.1 T2V qua Replicate...")
                output = await asyncio.to_thread(
                    replicate.run,
                    "wan-video/wan-2.1-1.3b",
                    input={
                        "prompt": prompt,
                        "aspect_ratio": aspect_ratio
                    }
                )
                if output:
                    video_url = output if isinstance(output, str) else output[0]
                    await self._download_video(str(video_url), output_path)
                    return output_path
            except Exception as e:
                logger.warning(f"Wan2.1 Replicate T2V lỗi: {e}")

        # 3. Fallback sang Semantic Engine
        from app.providers.video.semantic_engine import SemanticMotionVideoEngine
        engine = SemanticMotionVideoEngine()
        return await engine.generate_text_to_video(
            prompt=prompt,
            output_path=output_path,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            seed=seed
        )
