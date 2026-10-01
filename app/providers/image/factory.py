import os
from typing import Optional
from app.providers.image.base import ImageGenerationProvider
from app.providers.image.gemini_imagen import GeminiImagenProvider
from app.providers.image.dalle import OpenAIDalle3Provider
from app.providers.image.real_media import RealVisualMediaEngine
from app.providers.image.neural_synthesizer import NeuralProceduralSynthesizer
from app.config import settings

def get_image_provider(preference: Optional[str] = None, model: Optional[str] = None) -> ImageGenerationProvider:
    """
    Lựa chọn Image Provider thông minh & bền bỉ 100%:
    - Mặc định AUTO: Real Visual Media Engine (Ảnh thật chất lượng cao, 0 đồng, không lo quota)
    - Chỉ định DALL-E: OpenAIDalle3Provider (có auto-fallback)
    - Chỉ định Gemini: GeminiImagenProvider (nếu đã nạp Google billing)
    """
    m = (model or preference or "auto").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    fal_key = os.getenv("FAL_KEY") or settings.FAL_KEY

    # 1. Người dùng chỉ định cụ thể DALL-E
    if "dalle" in m or "openai" in m:
        if openai_key:
            return OpenAIDalle3Provider(api_key=openai_key)

    # 2. Người dùng chỉ định Google Gemini / Imagen
    if "gemini" in m or "imagen" in m:
        if gemini_key:
            return GeminiImagenProvider(api_key=gemini_key)

    # 3. Người dùng chọn FLUX / Fal
    if "flux" in m or "fal" in m:
        if fal_key:
            from app.providers.image.fal import FalImageProvider
            return FalImageProvider(api_key=fal_key)

    # 4. Mặc định AUTO:
    # RealVisualMediaEngine (Ảnh thật quang học 100% bám sát kịch bản, 0đ, không phụ thuộc quota API)
    return RealVisualMediaEngine()
