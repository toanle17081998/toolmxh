import os
from typing import Optional
from app.providers.image.base import ImageGenerationProvider
from app.providers.image.dalle import OpenAIDalle3Provider
from app.providers.image.gemini_imagen import GeminiImagenProvider
from app.providers.image.flux_free import FluxFreeImageProvider
from app.providers.image.neural_synthesizer import NeuralProceduralSynthesizer
from app.config import settings

def get_image_provider(preference: Optional[str] = None, model: Optional[str] = None) -> ImageGenerationProvider:
    """
    Lựa chọn Image Provider: Ưu tiên AI Image SOTA bám sát 100% kịch bản
    1. OpenAI DALL-E 3 (nếu có OPENAI_API_KEY)
    2. Google Imagen / Gemini Vision (nếu có GEMINI_API_KEY)
    3. FLUX.1 Free AI Generator (bám sát chi tiết kịch bản, không cần key)
    """
    m = (model or preference or "auto").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    fal_key = os.getenv("FAL_KEY") or settings.FAL_KEY

    # 1. Chỉ định DALL-E
    if "dalle" in m or "openai" in m:
        if openai_key:
            return OpenAIDalle3Provider(api_key=openai_key)

    # 2. Chỉ định Google Imagen / Gemini
    if "gemini" in m or "imagen" in m:
        if gemini_key:
            return GeminiImagenProvider(api_key=gemini_key)

    # 3. Chỉ định FLUX
    if "flux" in m:
        if fal_key:
            from app.providers.image.fal import FalImageProvider
            return FalImageProvider(api_key=fal_key)
        return FluxFreeImageProvider()

    # 4. Mặc định tự động (Smart Auto Hierarchy):
    # Ưu tiên DALL-E 3 nếu có key OpenAI
    if openai_key:
        return OpenAIDalle3Provider(api_key=openai_key)

    # Nếu có Gemini Key
    if gemini_key:
        return GeminiImagenProvider(api_key=gemini_key)

    # Fallback miễn phí: FLUX.1 AI Generation
    return FluxFreeImageProvider()
