import os
from pathlib import Path
from typing import Optional
from google import genai
from app.providers.image.base import ImageGenerationProvider
from app.config import settings

class GeminiImagenProvider(ImageGenerationProvider):
    """Mô hình tạo ảnh AI Google Imagen 3 sử dụng official google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiImagenProvider")
        self.client = genai.Client(api_key=self.api_key)

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

        result = self.client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=dict(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="9:16" if height > width else "16:9"
            )
        )
        image_bytes = result.generated_images[0].image.image_bytes
        with open(out_path, "wb") as f:
            f.write(image_bytes)
        return str(out_path)
