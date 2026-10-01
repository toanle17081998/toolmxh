import os
import asyncio
import logging
from typing import Optional
from app.providers.tts.base import TTSProvider
from app.providers.tts.gemini import GeminiTTSProvider
from app.providers.tts.edge import EdgeTTSProvider
from app.providers.tts.google import GoogleTTSProvider
from app.config import settings

logger = logging.getLogger(__name__)

class MasterTTSProvider(TTSProvider):
    """Provider giọng đọc Studio cao cấp: Khóa chặt 1 giọng đọc duy nhất cho toàn bộ video, tuyệt đối không nhảy giọng."""

    def __init__(self, voice_preference: str = "namminh"):
        self.gemini = None
        gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if gemini_key:
            self.gemini = GeminiTTSProvider(api_key=gemini_key)
        self.edge = EdgeTTSProvider()
        self.google = GoogleTTSProvider()
        self.voice_preference = voice_preference
        self.gemini_disabled = False
        # Khóa cứng provider và voice được chọn cho toàn bộ dự án video
        self._locked_provider: Optional[TTSProvider] = None
        self._locked_voice: Optional[str] = None

    async def synthesize_to_file(
        self,
        text: str,
        output_wav_path: str,
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> float:
        # Nếu đã khóa engine cho video này, luôn dùng duy nhất engine đó
        if self._locked_provider is not None:
            for retry in range(3):
                try:
                    return await self._locked_provider.synthesize_to_file(
                        text, output_wav_path, voice=self._locked_voice, speed=speed
                    )
                except Exception as e:
                    logger.warning(f"Lỗi đọc audio với locked provider (thử lại {retry+1}/3): {e}")
                    await asyncio.sleep(1.0)
            # Nếu retry 3 lần vẫn lỗi, thử lại lần cuối
            return await self._locked_provider.synthesize_to_file(
                text, output_wav_path, voice=self._locked_voice, speed=speed
            )

        # Cảnh đầu tiên: Lựa chọn và khóa chặt engine tốt nhất cho toàn bộ video
        v = (voice or self.voice_preference or "namminh").lower()
        openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY

        # 1. Nếu chọn OpenAI HD và có key hợp lệ
        if v in ["onyx", "nova", "shimmer", "alloy", "echo", "fable"] and openai_key:
            try:
                from app.providers.tts.openai import OpenAITTSProvider
                openai_tts = OpenAITTSProvider(api_key=openai_key)
                dur = await openai_tts.synthesize_to_file(text, output_wav_path, voice=v, speed=speed)
                self._locked_provider = openai_tts
                self._locked_voice = v
                return dur
            except Exception as e:
                logger.warning(f"OpenAI TTS không khả dụng ({e}), chuyển sang giải pháp khác...")

        # 2. Nếu chọn Gemini Studio (charon, kore, puck, aoede, fenrir)
        if any(k in v for k in ["charon", "kore", "puck", "aoede", "fenrir"]) and gemini_key and not self.gemini_disabled:
            if not self.gemini:
                self.gemini = GeminiTTSProvider(api_key=gemini_key)
            try:
                dur = await self.gemini.synthesize_to_file(text, output_wav_path, voice=v, speed=speed)
                self._locked_provider = self.gemini
                self._locked_voice = v
                return dur
            except Exception as e:
                self.gemini_disabled = True
                logger.warning(f"Gemini TTS không phản hồi ({e}), chuyển sang Studio Neural...")

        # 3. Microsoft Edge-TTS Neural (NamMinh / HoaiMy)
        edge_voice = "vi-VN-NamMinhNeural" if any(k in v for k in ["nam", "charon", "fenrir", "puck", "onyx", "echo"]) else "vi-VN-HoaiMyNeural"
        try:
            dur = await self.edge.synthesize_to_file(text, output_wav_path, edge_voice, speed)
            self._locked_provider = self.edge
            self._locked_voice = edge_voice
            return dur
        except Exception as e:
            logger.warning(f"Edge-TTS gặp sự cố mạng ({e}), chuyển sang Google Studio fallback...")

        # 4. Fallback cuối cùng: Google TTS (Khóa chặt cho toàn bộ video để không bị đổi giọng)
        dur = await self.google.synthesize_to_file(text, output_wav_path, "vi", speed)
        self._locked_provider = self.google
        self._locked_voice = "vi"
        return dur

def get_tts_provider(voice: str = "onyx") -> TTSProvider:
    return MasterTTSProvider(voice_preference=voice)
