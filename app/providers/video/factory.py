import os
from app.providers.video.base import GenerativeVideoProvider
from app.providers.video.motion_engine import CinematicMotionVideoEngine
from app.providers.video.comfyui import ComfyUIVideoProvider
from app.providers.video.veo import GoogleVeoVideoProvider
from app.config import settings

def get_video_provider(preference: str = "AUTO") -> GenerativeVideoProvider:
    """Tự động lựa chọn Video Engine mạnh nhất: Google Veo 2 -> ComfyUI Wan2.1 -> Cinematic Motion Engine."""
    pref = preference.upper()
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY

    # Nếu chọn VEO hoặc cấu hình video model là VEO
    if (pref == "VEO" or pref == "GOOGLE") and gemini_key:
        try:
            return GoogleVeoVideoProvider(api_key=gemini_key)
        except Exception:
            pass

    if pref == "COMFYUI":
        return ComfyUIVideoProvider(server_url=settings.COMFYUI_SERVER_URL)

    return CinematicMotionVideoEngine()
