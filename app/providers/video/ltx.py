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

class LTXVideoProvider(GenerativeVideoProvider):
    """
    LTX-Video Provider từ Lightricks:
    Mô hình DiT (Diffusion Transformer) sinh video thời gian thực siêu nhanh (Real-Time Video Generation).
    Hỗ trợ cả Text-to-Video và Image-to-Video.
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
        """Sinh video từ ảnh bằng LTX-Video."""
        # 1. Thử qua Fal.ai
        if self.fal_key:
            try:
                import fal_client
                os.environ["FAL_KEY"] = self.fal_key
                logger.info(f"Đang gọi LTX-Video I2V qua Fal.ai: '{prompt[:60]}...'")
                image_url = await asyncio.to_thread(fal_client.upload_file, image_path)

                handler = await asyncio.to_thread(
                    fal_client.submit,
                    "fal-ai/ltx-video/image-to-video",
                    arguments={
                        "image_url": image_url,
                        "prompt": prompt,
                    }
                )
                result = await asyncio.to_thread(handler.get)
                video_url = result.get("video", {}).get("url")
                if video_url:
                    await self._download_video(video_url, output_path)
                    return output_path
            except Exception as e:
                logger.warning(f"LTX-Video Fal.ai I2V lỗi: {e}")

        # 2. Thử qua Replicate
        if self.replicate_token:
            try:
                import replicate
                os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
                logger.info(f"Đang gọi LTX-Video qua Replicate...")
                with open(image_path, "rb") as img_file:
                    output = await asyncio.to_thread(
                        replicate.run,
                        "lightricks/ltx-video",
                        input={
                            "input_image": img_file,
                            "prompt": prompt
                        }
                    )
                if output:
                    video_url = output if isinstance(output, str) else output[0]
                    await self._download_video(str(video_url), output_path)
                    return output_path
            except Exception as e:
                logger.warning(f"LTX-Video Replicate I2V lỗi: {e}")

        # 3. Fallback sang Semantic Engine
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
        """Sinh video từ Text Prompt bằng LTX-Video."""
        if self.fal_key:
            try:
                import fal_client
                os.environ["FAL_KEY"] = self.fal_key
                logger.info(f"Đang gọi LTX-Video T2V qua Fal.ai...")
                result = await asyncio.to_thread(
                    fal_client.subscribe,
                    "fal-ai/ltx-video",
                    arguments={
                        "prompt": prompt
                    }
                )
                video_url = result.get("video", {}).get("url")
                if video_url:
                    await self._download_video(video_url, output_path)
                    return output_path
            except Exception as e:
                logger.warning(f"LTX-Video Fal.ai T2V lỗi: {e}")

        if self.replicate_token:
            try:
                import replicate
                os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
                logger.info(f"Đang gọi LTX-Video T2V qua Replicate...")
                output = await asyncio.to_thread(
                    replicate.run,
                    "lightricks/ltx-video",
                    input={
                        "prompt": prompt
                    }
                )
                if output:
                    video_url = output if isinstance(output, str) else output[0]
                    await self._download_video(str(video_url), output_path)
                    return output_path
            except Exception as e:
                logger.warning(f"LTX-Video Replicate T2V lỗi: {e}")

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
