import os
from typing import Optional
from app.providers.image.base import ImageGenerationProvider
from app.providers.image.gemini_imagen import GeminiImagenProvider
from app.providers.image.dalle import OpenAIDalle3Provider
from app.providers.image.opencut_realistic import OpenCutRealisticImageProvider
from app.config import settings

def get_image_provider(preference: Optional[str] = None, model: Optional[str] = None) -> ImageGenerationProvider:
    """Lựa chọn Image Provider: OpenCut Realistic Master -> Fal.ai FLUX -> Gemini Pro Image -> DALL-E 3."""
    m = (model or preference or "AUTO").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    fal_key = os.getenv("FAL_KEY") or settings.FAL_KEY

    # 1. OpenCut Cinematic Realistic Master (Mặc định chuẩn phim chân thực, sắc nét 1080x1920)
    if any(k in m for k in ["opencut", "realistic", "master", "cinematic_master"]):
        return OpenCutRealisticImageProvider()

    # 2. Fal.ai FLUX (Theo kiến trúc đối tác của OpenCut)
    if "fal" in m or "flux" in m:
        if fal_key:
            from app.providers.image.fal import FalImageProvider
            return FalImageProvider(api_key=fal_key)
        else:
            return OpenCutRealisticImageProvider()

    # 3. Offline Semantic Neural Canvas
    if m in ["neural", "canvas", "offline", "procedural"]:
        return OpenCutRealisticImageProvider()

    # 3. OpenAI DALL-E 3
    if "dalle" in m or "openai" in m:
        if openai_key:
            return OpenAIDalle3Provider(api_key=openai_key)
        elif gemini_key:
            return GeminiImagenProvider(api_key=gemini_key, model="gemini-3-pro-image-preview")
        else:
            return OpenCutRealisticImageProvider()

    # 4. Google Gemini Pro Image
    if "gemini" in m or "imagen" in m:
        if gemini_key:
            return GeminiImagenProvider(api_key=gemini_key, model=model or "gemini-3-pro-image-preview")
        elif openai_key:
            return OpenAIDalle3Provider(api_key=openai_key)
        else:
            return OpenCutRealisticImageProvider()

    # 5. Mặc định
    if fal_key:
        from app.providers.image.fal import FalImageProvider
        return FalImageProvider(api_key=fal_key)
    if gemini_key:
        return GeminiImagenProvider(api_key=gemini_key, model="gemini-3-pro-image-preview")
    elif openai_key:
        return OpenAIDalle3Provider(api_key=openai_key)
    return OpenCutRealisticImageProvider()
