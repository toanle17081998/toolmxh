from app.providers.video.base import GenerativeVideoProvider
from app.providers.video.motion_engine import CinematicMotionVideoEngine
from app.providers.video.comfyui import ComfyUIVideoProvider
from app.config import settings

def get_video_provider(preference: str = "AUTO") -> GenerativeVideoProvider:
    """Tự động lựa chọn Video Engine: ưu tiên ComfyUI nếu được yêu cầu và khả dụng, nếu không dùng Cinematic Motion Engine."""
    pref = preference.upper()
    if pref == "COMFYUI":
        return ComfyUIVideoProvider(server_url=settings.COMFYUI_SERVER_URL)
    return CinematicMotionVideoEngine()
