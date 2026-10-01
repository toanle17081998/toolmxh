import os
from typing import Optional
from app.providers.video.base import GenerativeVideoProvider
from app.providers.video.wan import WanVideoProvider
from app.providers.video.ltx import LTXVideoProvider
from app.providers.video.hunyuan import HunyuanVideoProvider
from app.providers.video.semantic_engine import SemanticMotionVideoEngine
from app.providers.video.motion_engine import CinematicMotionVideoEngine
from app.providers.video.comfyui import ComfyUIVideoProvider
from app.providers.video.veo import GoogleVeoVideoProvider
from app.config import settings

def get_video_provider(preference: str = "wan2.1", model: Optional[str] = None) -> GenerativeVideoProvider:
    """
    Tự động lựa chọn Video Engine AI hàng đầu:
    1. Wan-Video (Wan2.1 / Wan2.2 - Alibaba SOTA)
    2. LTX-Video (Lightricks Real-Time DiT)
    3. HunyuanVideo (Tencent High-Definition)
    4. Semantic Motion Video Engine (100% bám sát nội dung kịch bản)
    """
    pref = (model or preference or "wan2.1").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    fal_key = os.getenv("FAL_KEY") or settings.FAL_KEY
    replicate_token = os.getenv("REPLICATE_API_TOKEN") or settings.REPLICATE_API_TOKEN

    # 1. Wan-Video (Wan 2.1 & Wan 2.2)
    if any(k in pref for k in ["wan", "wan2", "wan2.1", "wan2.2"]):
        model_size = "14b" if "14b" in pref else "1.3b"
        return WanVideoProvider(model_size=model_size, fal_key=fal_key, replicate_token=replicate_token)

    # 2. LTX-Video (Lightricks)
    if any(k in pref for k in ["ltx", "lightricks"]):
        return LTXVideoProvider(fal_key=fal_key, replicate_token=replicate_token)

    # 3. HunyuanVideo (Tencent)
    if any(k in pref for k in ["hunyuan", "tencent"]):
        return HunyuanVideoProvider(fal_key=fal_key, replicate_token=replicate_token)

    # 4. Google Veo 3.1
    if "veo" in pref:
        if gemini_key:
            return GoogleVeoVideoProvider(api_key=gemini_key, model=model or "veo-3.1-generate-preview")
        else:
            return SemanticMotionVideoEngine()

    # 5. ComfyUI Server
    if "comfy" in pref:
        return ComfyUIVideoProvider(server_url=settings.COMFYUI_SERVER_URL)

    # 6. Nếu có Fal hoặc Replicate key, mặc định dùng Wan 2.1
    if fal_key or replicate_token:
        return WanVideoProvider(model_size="1.3b", fal_key=fal_key, replicate_token=replicate_token)

    # 7. Mặc định bền vững: Semantic Cinematic Engine (Khớp 100% kịch bản, không lấy stock ngẫu nhiên)
    return SemanticMotionVideoEngine()
