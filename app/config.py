from pathlib import Path
import os
import shutil
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

# Tự động nạp proxy công ty nếu phát hiện mạng nội bộ
if "HTTP_PROXY" not in os.environ and "http_proxy" not in os.environ:
    os.environ["HTTP_PROXY"] = "http://172.16.120.13:3128"
    os.environ["HTTPS_PROXY"] = "http://172.16.120.13:3128"

class Settings(BaseSettings):
    # App & Workdirs
    APP_NAME: str = "Vietnamese Generative Video Factory"
    WORKSPACE_DIR: Path = Path("d:/workspace/toolmxh")
    OUTPUTS_DIR: Path = Path("d:/workspace/toolmxh/outputs")
    PROJECTS_DIR: Path = Path("d:/workspace/toolmxh/outputs/projects")
    ASSETS_DIR: Path = Path("d:/workspace/toolmxh/assets")

    # API Keys
    GEMINI_API_KEY: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    OPENAI_API_KEY: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    FAL_KEY: Optional[str] = Field(default=None, alias="FAL_KEY")
    REPLICATE_API_TOKEN: Optional[str] = Field(default=None, alias="REPLICATE_API_TOKEN")

    # ComfyUI Local / Remote Server
    COMFYUI_SERVER_URL: str = "http://127.0.0.1:8188"
    COMFYUI_WS_URL: str = "ws://127.0.0.1:8188/ws"

    # Default Providers
    DEFAULT_LLM_PROVIDER: str = "gemini"  # "gemini" | "openai"
    DEFAULT_LLM_MODEL: str = "gemini-3.8-flash"
    DEFAULT_TTS_PROVIDER: str = "edge"    # "edge" | "gemini" | "google"
    DEFAULT_TTS_VOICE: str = "namminh"    # "namminh" | "hoaimy" | "charon"
    DEFAULT_IMAGE_PROVIDER: str = "auto"  # "auto" | "fal" | "comfyui" | "diffusers"
    DEFAULT_VIDEO_PROVIDER: str = "auto"  # "auto" | "wan" | "ltx" | "fal" | "comfyui"

    # Platform presets
    PLATFORM_RESOLUTIONS: dict = {
        "tiktok": (1080, 1920),
        "shorts": (1080, 1920),
        "reels": (1080, 1920),
        "youtube": (1920, 1080)
    }

    # GPU Worker Configuration
    MAX_CONCURRENT_GPU_JOBS: int = 1
    AUTO_OFFLOAD_CUDA_CACHE: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

def get_ffmpeg_binary() -> str:
    """Tự động phát hiện FFmpeg trên hệ thống, fallback sang imageio-ffmpeg nếu chưa có trong PATH."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"
