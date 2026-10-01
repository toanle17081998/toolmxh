import logging
from app.providers.tts.base import TTSProvider
from app.providers.tts.edge import EdgeTTSProvider
from app.providers.tts.google import GoogleTTSProvider

logger = logging.getLogger(__name__)

class ResilientTTSProvider(TTSProvider):
    """Provider tự động chuyển đổi: Ưu tiên Edge-TTS, tự động fallback sang Google TTS nếu WebSocket bị chặn."""

    def __init__(self):
        self.edge = EdgeTTSProvider()
        self.google = GoogleTTSProvider()
        self.use_google_direct = False

    async def synthesize_to_file(
        self,
        text: str,
        output_wav_path: str,
        voice: str = "vi-VN-HoaiMyNeural",
        speed: float = 1.0
    ) -> float:
        if self.use_google_direct:
            return await self.google.synthesize_to_file(text, output_wav_path, "vi", speed)

        try:
            return await self.edge.synthesize_to_file(text, output_wav_path, voice, speed)
        except Exception as e:
            logger.warning(f"Edge-TTS gặp lỗi mạng ({e}), tự động chuyển sang Google TTS...")
            self.use_google_direct = True
            return await self.google.synthesize_to_file(text, output_wav_path, "vi", speed)

def get_tts_provider() -> TTSProvider:
    return ResilientTTSProvider()
