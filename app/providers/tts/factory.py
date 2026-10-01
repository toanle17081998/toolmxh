import os
import logging
from typing import Optional
from app.providers.tts.base import TTSProvider
from app.providers.tts.gemini import GeminiTTSProvider
from app.providers.tts.edge import EdgeTTSProvider
from app.providers.tts.google import GoogleTTSProvider
from app.config import settings

logger = logging.getLogger(__name__)

class MasterTTSProvider(TTSProvider):
    """Provider giọng đọc Studio cao cấp: Ưu tiên Gemini Studio Neural Voice & OpenAI HD."""

    def __init__(self, voice_preference: str = "onyx"):
        self.gemini = None
        gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if gemini_key:
            self.gemini = GeminiTTSProvider(api_key=gemini_key)
        self.edge = EdgeTTSProvider()
        self.google = GoogleTTSProvider()
        self.voice_preference = voice_preference

    async def synthesize_to_file(
        self,
        text: str,
        output_wav_path: str,
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> float:
        v = (voice or self.voice_preference or "onyx").lower()
        openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY

        # 0. Nếu người dùng chọn engine từ VoiceStudio (CosyVoice 2/3, Kokoro, F5-TTS)
        if v in ["voicestudio", "cosyvoice", "kokoro", "f5tts"] or v.startswith("voicestudio:"):
            try:
                from app.providers.tts.voicestudio import VoiceStudioProvider
                engine_name = v.split(":")[-1] if ":" in v else "cosyvoice"
                vs_provider = VoiceStudioProvider()
                return await vs_provider.synthesize_to_file(text, output_wav_path, voice=engine_name, speed=speed)
            except Exception as e:
                logger.warning(f"VoiceStudio không khả dụng ({e}), chuyển sang Gemini/OpenAI...")

        # 1. Ưu tiên Google Gemini Studio Neural Voice (Cực hay, trầm ấm/truyền cảm, âm thanh 24kHz -> 44.1kHz studio)
        if gemini_key:
            try:
                if not self.gemini:
                    self.gemini = GeminiTTSProvider(api_key=gemini_key)
                return await self.gemini.synthesize_to_file(text, output_wav_path, voice=v, speed=speed)
            except Exception as ge:
                logger.warning(f"Gemini Neural TTS gặp lỗi ({ge}), chuyển sang OpenAI/Edge fallback...")

        # 2. Thử OpenAI TTS HD nếu có key và quota
        if v in ["onyx", "nova", "shimmer", "alloy", "echo", "fable"] and openai_key:
            try:
                from app.providers.tts.openai import OpenAITTSProvider
                openai_tts = OpenAITTSProvider(api_key=openai_key)
                return await openai_tts.synthesize_to_file(text, output_wav_path, voice=v, speed=speed)
            except Exception as e:
                logger.warning(f"OpenAI TTS HD không khả dụng ({e}), tiếp tục fallback...")

        # 3. Ánh xạ giọng Edge-TTS Neural chuẩn truyền hình
        edge_voice = "vi-VN-NamMinhNeural" if "nam" in v or v == "onyx" else "vi-VN-HoaiMyNeural"
        try:
            return await self.edge.synthesize_to_file(text, output_wav_path, edge_voice, speed)
        except Exception as e:
            logger.warning(f"Edge-TTS gặp sự cố mạng ({e}), chuyển sang fallback cuối cùng...")

        # 4. Fallback cuối cùng
        return await self.google.synthesize_to_file(text, output_wav_path, "vi", speed)

def get_tts_provider(voice: str = "onyx") -> TTSProvider:
    return MasterTTSProvider(voice_preference=voice)
