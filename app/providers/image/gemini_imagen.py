import os
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from app.providers.image.base import ImageGenerationProvider
from app.config import settings

import base64
import logging

logger = logging.getLogger(__name__)

class GeminiImagenProvider(ImageGenerationProvider):
    """Mô hình tạo ảnh AI đỉnh cao Google Pro Image (gemini-3-pro-image-preview, gemini-3.1-flash-image, Imagen 3)."""

    supports_health_characters = True

    @property
    def supports_reference_images(self):
        return "imagen" not in self.model.lower()

    async def generate_health_image(self, prompt, output_path, width=1080, height=1920,
                                    seed=-1, reference_images=None):
        import asyncio
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.supports_reference_images:
            result = await asyncio.to_thread(
                self.client.models.generate_images, model=self.model, prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1, output_mime_type="image/png",
                                                 aspect_ratio="9:16" if height > width else "16:9"),
            )
            out_path.write_bytes(result.generated_images[0].image.image_bytes)
            return str(out_path)
        contents = [prompt]
        for path in reference_images or []:
            contents.append(types.Part.from_bytes(data=Path(path).read_bytes(), mime_type="image/png"))
        result = await asyncio.to_thread(
            self.client.models.generate_content, model=self.model, contents=contents,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )
        for candidate in getattr(result, "candidates", []) or []:
            for part in getattr(candidate.content, "parts", []) or []:
                if getattr(part, "inline_data", None):
                    data = part.inline_data.data
                    out_path.write_bytes(base64.b64decode(data) if isinstance(data, str) else data)
                    return str(out_path)
        raise RuntimeError("Health character image generation returned no image; no stock fallback permitted")

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
            logger.warning(f"Google Image Generation ({self.model}) gặp giới hạn quota ({e}), chuyển sang fallback an toàn...")
            from app.providers.image.real_media import RealVisualMediaEngine
            return await RealVisualMediaEngine().generate_image(prompt, output_path, width, height, seed)
