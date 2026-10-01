import os
from app.providers.image.base import ImageGenerationProvider
from app.providers.image.gemini_imagen import GeminiImagenProvider
from app.providers.image.dalle import OpenAIDalle3Provider
from app.providers.image.neural_synthesizer import NeuralProceduralSynthesizer
from app.config import settings

def get_image_provider(preference: str = "AUTO") -> ImageGenerationProvider:
    """Tự động chọn Image Provider mạnh nhất: Gemini Imagen 3 -> OpenAI DALL-E 3 HD -> Neural Canvas."""
    pref = preference.upper()
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY

    if (pref == "IMAGEN" or pref == "GEMINI" or pref == "AUTO") and gemini_key:
        try:
            return GeminiImagenProvider(api_key=gemini_key)
        except Exception:
            pass

    if (pref == "DALLE" or pref == "OPENAI" or pref == "AUTO") and openai_key:
        try:
            return OpenAIDalle3Provider(api_key=openai_key)
        except Exception:
            pass

    return NeuralProceduralSynthesizer()
