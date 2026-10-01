import os
from typing import Optional
from app.providers.video.base import GenerativeVideoProvider
from app.providers.video.motion_engine import CinematicMotionVideoEngine
from app.providers.video.comfyui import ComfyUIVideoProvider
from app.providers.video.veo import GoogleVeoVideoProvider
from app.providers.video.real_footage import RealFootageVideoEngine
from app.config import settings

def get_video_provider(preference: str = "opencut_real", model: Optional[str] = None) -> GenerativeVideoProvider:
    """Tự động lựa chọn Video Engine: OpenCut Real Video Footage -> Fal.ai -> Google Veo -> ComfyUI -> Motion Engine."""
    pref = (model or preference or "opencut_real").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    fal_key = os.getenv("FAL_KEY") or settings.FAL_KEY

    # 1. Fal.ai Video (Minimax / Kling / Luma)
    if "fal" in pref:
        if fal_key:
            from app.providers.video.fal import FalVideoProvider
            return FalVideoProvider(api_key=fal_key)
        else:
            return RealFootageVideoEngine()

    # 2. Google Veo 3.1 Video
    if "veo" in pref:
        if gemini_key:
            return GoogleVeoVideoProvider(api_key=gemini_key, model=model or "veo-3.1-generate-preview")
        else:
            return RealFootageVideoEngine()

    # 3. ComfyUI Server
    if "comfy" in pref:
        return ComfyUIVideoProvider(server_url=settings.COMFYUI_SERVER_URL)

    # 4. Chế độ chỉ dùng ảnh tĩnh di chuyển (Ken Burns / Motion Camera)
    if any(k in pref for k in ["kenburns", "still_motion", "still"]):
        return CinematicMotionVideoEngine()

    # 5. Mặc định: OpenCut-Style Real Motion Video Engine (Video chuyển động thật 100%, không phải ảnh di chuyển)
    return RealFootageVideoEngine()

