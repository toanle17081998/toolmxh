import os
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from app.providers.image.base import ImageGenerationProvider
from app.config import settings

import base64
import logging
from app.providers.image.neural_synthesizer import NeuralProceduralSynthesizer

logger = logging.getLogger(__name__)

class GeminiImagenProvider(ImageGenerationProvider):
    """Mô hình tạo ảnh AI đỉnh cao Google Pro Image (gemini-3-pro-image-preview, gemini-3.1-flash-image, Imagen 3)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3-pro-image-preview"):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY không được tìm thấy cho Google Image Generation.")
        self.client = genai.Client(api_key=self.api_key)
        self.model = model

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

        aspect_ratio = "9:16" if height > width else "16:9"
        enhanced_prompt = (
            f"Hyper-realistic cinematic film still, masterpiece vertical photography, 8k resolution: {prompt}. "
            "Natural dramatic lighting, volumetric depth, award winning cinematography, sharp focus."
        )

        try:
            # 1. Nếu dùng các model Imagen (imagen-3.0-generate-002...)
            if "imagen" in self.model.lower():
                result = self.client.models.generate_images(
                    model=self.model,
                    prompt=enhanced_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/png",
                        aspect_ratio=aspect_ratio,
                        person_generation="ALLOW_ADULT"
                    )
                )
                image_bytes = result.generated_images[0].image.image_bytes
                with open(out_path, "wb") as f:
                    f.write(image_bytes)
                return str(out_path)

            # 2. Nếu dùng các model Gemini Multimodal Image Generation (gemini-3-pro-image-preview, gemini-3.1-flash-image...)
            result = self.client.models.generate_content(
                model=self.model,
                contents=enhanced_prompt
            )
            for cand in getattr(result, "candidates", []):
                for part in getattr(cand.content, "parts", []):
                    if hasattr(part, "inline_data") and part.inline_data:
                        raw_data = part.inline_data.data
                        if isinstance(raw_data, str):
                            raw_data = base64.b64decode(raw_data)
                        with open(out_path, "wb") as f:
                            f.write(raw_data)
                        return str(out_path)
            raise RuntimeError(f"Model {self.model} không trả về phần tử ảnh inline_data.")

        except Exception as e:
            logger.warning(f"Google Image Generation ({self.model}) gặp giới hạn quota hoặc lỗi ({e}), chuyển sang fallback...")
            
            # Fallback sang OpenAI DALL-E 3 nếu có key
            openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
            if openai_key:
                try:
                    from app.providers.image.dalle import OpenAIDalle3Provider
                    dalle = OpenAIDalle3Provider(api_key=openai_key)
                    return await dalle.generate_image(prompt, output_path, width, height, seed, negative_prompt)
                except Exception as de:
                    logger.warning(f"OpenAI DALL-E 3 fallback lỗi: {de}")

            # Fallback cuối cùng sang Neural Procedural Synthesizer 1080x1920
            neural = NeuralProceduralSynthesizer()
            return await neural.generate_image(prompt, output_path, width, height, seed, negative_prompt)
