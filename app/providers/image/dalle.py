import os
import urllib.request
from pathlib import Path
from typing import Optional
from openai import OpenAI
from app.providers.image.base import ImageGenerationProvider
from app.config import settings

class OpenAIDalle3Provider(ImageGenerationProvider):
    """Mô hình tạo ảnh DALL-E 3 HD (1024x1792 dọc) chất lượng cao nhất của OpenAI."""

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

        # DALL-E 3 hỗ trợ native tỉ lệ dọc 1024x1792
        size = "1024x1792" if height > width else "1792x1024"
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
