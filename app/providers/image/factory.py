import os
from app.providers.image.base import ImageGenerationProvider
from app.providers.image.gemini_imagen import GeminiImagenProvider
from app.providers.image.dalle import OpenAIDalle3Provider
from app.providers.image.neural_synthesizer import NeuralProceduralSynthesizer
from app.config import settings

def get_image_provider(preference: Optional[str] = None, model: Optional[str] = None) -> ImageGenerationProvider:
    """Lựa chọn Image Provider theo model yêu cầu: Gemini Pro Image / DALL-E 3 / Neural Canvas."""
    m = (model or preference or "AUTO").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY

    # 1. Offline Neural Canvas
    if m in ["neural", "canvas", "offline", "procedural"]:
        return NeuralProceduralSynthesizer()

    # 2. OpenAI DALL-E 3
    if "dalle" in m or "openai" in m:
        if openai_key:
            return OpenAIDalle3Provider(api_key=openai_key)
        elif gemini_key:
            return GeminiImagenProvider(api_key=gemini_key, model="gemini-3-pro-image-preview")
        else:
            return NeuralProceduralSynthesizer()

    # 3. Google Gemini Pro Image / Imagen 3
    if "gemini" in m or "imagen" in m:
        if gemini_key:
            return GeminiImagenProvider(api_key=gemini_key, model=model or "gemini-3-pro-image-preview")
        elif openai_key:
            return OpenAIDalle3Provider(api_key=openai_key)
        else:
            return NeuralProceduralSynthesizer()

    # 4. Mặc định ưu tiên Gemini nếu có key, rồi OpenAI, rồi Neural
    if gemini_key:
        return GeminiImagenProvider(api_key=gemini_key, model="gemini-3-pro-image-preview")
    elif openai_key:
        return OpenAIDalle3Provider(api_key=openai_key)
    return NeuralProceduralSynthesizer()
