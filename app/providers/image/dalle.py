import os
import logging
import urllib.request
from pathlib import Path
from typing import Optional
from openai import OpenAI
from app.providers.image.base import ImageGenerationProvider
from app.config import settings

logger = logging.getLogger(__name__)

class OpenAIDalle3Provider(ImageGenerationProvider):
    """Mô hình tạo ảnh DALL-E của OpenAI (Hỗ trợ DALL-E 3 và tự động fallback nếu hết credit hoặc model không khả dụng)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY không được tìm thấy cho DALL-E 3.")
        self.client = OpenAI(api_key=self.api_key)

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1,
        negative_prompt: str = ""
    ) -> str:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Thử gọi DALL-E 3
        try:
            size = "1024x1792" if height > width else "1792x1024"
            logger.info("Đang gọi OpenAI DALL-E 3...")
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=f"Cinematic photorealistic 8k, hyper-detailed, masterpiece: {prompt}",
                size=size,
                quality="hd",
                n=1
            )
            image_url = response.data[0].url
            req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as res:
                with open(out_path, "wb") as f:
                    f.write(res.read())
            return str(out_path)

        except Exception as e:
            logger.warning(f"OpenAI DALL-E 3 gặp sự cố ({e}). Đang thử chế độ dự phòng...")

            # 2. Thử DALL-E 2 nếu model 3 không tồn tại
            try:
                logger.info("Đang thử DALL-E 2 (1024x1024)...")
                response = self.client.images.generate(
                    model="dall-e-2",
                    prompt=f"Cinematic masterpiece: {prompt[:350]}",
                    size="1024x1024",
                    n=1
                )
                image_url = response.data[0].url
                req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as res:
                    with open(out_path, "wb") as f:
                        f.write(res.read())
                return str(out_path)
            except Exception as e2:
                logger.warning(f"OpenAI DALL-E 2 cũng gặp sự cố ({e2}). Chuyển sang Google Imagen / Visual Engine...")

            # 3. Fallback sang Real Visual Media Engine (Đa dạng thông minh)
            try:
                from app.providers.image.real_media import RealVisualMediaEngine
                real_engine = RealVisualMediaEngine()
                return await real_engine.generate_image(prompt, output_path, width, height, seed, negative_prompt)
            except Exception as re:
                logger.warning(f"RealVisualMediaEngine fallback gặp lỗi: {re}")

            # 4. Fallback cuối cùng không bao giờ sập
            from app.providers.image.neural_synthesizer import NeuralProceduralSynthesizer
            neural = NeuralProceduralSynthesizer()
            return await neural.generate_image(prompt, output_path, width, height, seed, negative_prompt)
