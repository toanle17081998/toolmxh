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

class HunyuanVideoProvider(GenerativeVideoProvider):
    """
    HunyuanVideo Provider từ Tencent:
    Mô hình tạo video điện ảnh độ phân giải cao SOTA (13B parameters) của Tencent.
    """

    def __init__(
        self,
        fal_key: Optional[str] = None,
        replicate_token: Optional[str] = None
    ):
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
        # Hunyuan chủ yếu là Text-to-Video hoặc I2V
        return await self.generate_text_to_video(
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
        aspect_ratio = "9:16" if height >= width else "16:9"

        if self.fal_key:
            try:
                import fal_client
                os.environ["FAL_KEY"] = self.fal_key
                logger.info(f"Đang gọi Tencent HunyuanVideo qua Fal.ai...")
                result = await asyncio.to_thread(
                    fal_client.subscribe,
                    "fal-ai/hunyuan-video",
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
                logger.warning(f"Hunyuan Fal.ai T2V lỗi: {e}")

        if self.replicate_token:
            try:
                import replicate
                os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
                logger.info(f"Đang gọi Tencent HunyuanVideo qua Replicate...")
                output = await asyncio.to_thread(
                    replicate.run,
                    "tencent/hunyuan-video",
                    input={
                        "prompt": prompt
                    }
                )
                if output:
                    video_url = output if isinstance(output, str) else output[0]
                    await self._download_video(str(video_url), output_path)
                    return output_path
            except Exception as e:
                logger.warning(f"Hunyuan Replicate T2V lỗi: {e}")

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
