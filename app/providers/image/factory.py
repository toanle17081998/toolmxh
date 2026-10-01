import os
from app.providers.image.base import ImageGenerationProvider
from app.providers.image.gemini_imagen import GeminiImagenProvider
from app.providers.image.neural_synthesizer import NeuralProceduralSynthesizer
from app.config import settings

def get_image_provider() -> ImageGenerationProvider:
    """Tự động chọn image provider: nếu có GEMINI_API_KEY dùng Imagen 3, nếu không dùng Neural Canvas Synthesizer."""
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    if gemini_key:
        try:
            return GeminiImagenProvider(api_key=gemini_key)
        except Exception:
            pass
    return NeuralProceduralSynthesizer()
