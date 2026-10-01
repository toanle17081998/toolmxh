import os
from typing import Optional
from app.providers.video.base import GenerativeVideoProvider
from app.providers.video.motion_engine import CinematicMotionVideoEngine
from app.providers.video.comfyui import ComfyUIVideoProvider
from app.providers.video.veo import GoogleVeoVideoProvider
from app.config import settings

def get_video_provider(preference: str = "cinematic", model: Optional[str] = None) -> GenerativeVideoProvider:
    """Tự động lựa chọn Video Engine: Google Veo 3.1 -> ComfyUI Wan2.1 -> Lanczos Cinematic Motion Engine."""
    pref = (model or preference or "cinematic").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY

    # 1. Google Veo 3.1 Video
    if "veo" in pref:
        if gemini_key:
            return GoogleVeoVideoProvider(api_key=gemini_key, model=model or "veo-3.1-generate-preview")
        else:
            return CinematicMotionVideoEngine()

    # 2. ComfyUI Server
    if "comfy" in pref:
        return ComfyUIVideoProvider(server_url=settings.COMFYUI_SERVER_URL)

    # 3. Lanczos Cinematic Motion Engine (Nội bộ siêu nét)
    return CinematicMotionVideoEngine()
