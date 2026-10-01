import os
import base64
import subprocess
import wave
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from app.providers.tts.base import TTSProvider
from app.config import settings, get_ffmpeg_binary

class GeminiTTSProvider(TTSProvider):
    """Giọng đọc thuyết minh Studio cao cấp sử dụng Google Gemini Neural TTS (gemini-2.5-flash-preview-tts / gemini-3.8-flash-tts)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash-preview-tts"):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY không được tìm thấy cho Gemini TTS.")
        self.client = genai.Client(api_key=self.api_key)
        self.model = model

    async def synthesize_to_file(
        self,
        text: str,
        output_wav_path: str,
        voice: Optional[str] = "nam_tram",
        speed: float = 1.0
    ) -> float:
        out_path = Path(output_wav_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        raw_pcm_path = out_path.with_suffix(".temp.pcm")

        v_lower = (voice or "charon").lower()
        # Ánh xạ giọng chuẩn studio của Gemini
        if any(k in v_lower for k in ["kore", "nu_diudang", "female", "nova", "shimmer", "hoaimy"]):
            gemini_voice = "Kore"
        elif any(k in v_lower for k in ["aoede", "nu_tram", "nu_saulang"]):
            gemini_voice = "Aoede"
        elif any(k in v_lower for k in ["puck", "tretrung", "tiktok"]):
            gemini_voice = "Puck"
        elif any(k in v_lower for k in ["fenrir", "manhme"]):
            gemini_voice = "Fenrir"
        else: # Mặc định giọng nam trầm điện ảnh Charon
            gemini_voice = "Charon"

        models_to_try = [self.model, "gemini-2.5-flash-preview-tts", "gemini-3.8-flash-tts"]
        raw_bytes = None
        last_err = None

        for m in models_to_try:
            try:
                res = self.client.models.generate_content(
                    model=m,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=gemini_voice)
                            )
                        )
                    )
                )
                if res.candidates and res.candidates[0].content and res.candidates[0].content.parts:
                    for part in res.candidates[0].content.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            data = part.inline_data.data
                            if isinstance(data, str):
                                data = base64.b64decode(data)
                            raw_bytes = data
                            break
                if raw_bytes:
                    break
            except Exception as e:
                last_err = e
                # Fallback thử với prompt trực tiếp nếu speech_config gặp lỗi
                try:
                    res = self.client.models.generate_content(
                        model=m,
                        contents=f"Đọc to rõ ràng đoạn văn sau bằng tiếng Việt: {text}",
                        config=types.GenerateContentConfig(response_modalities=["AUDIO"])
                    )
                    for part in res.candidates[0].content.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            data = part.inline_data.data
                            if isinstance(data, str):
                                data = base64.b64decode(data)
                            raw_bytes = data
                            break
                    if raw_bytes:
                        break
                except Exception:
                    continue

        if not raw_bytes:
            raise last_err or RuntimeError("Gemini TTS không trả về dữ liệu audio.")

        with open(raw_pcm_path, "wb") as f:
            f.write(raw_bytes)

        # Chuyển đổi raw PCM 24kHz sang WAV 44.1kHz chuẩn studio bằng FFmpeg
        ffmpeg_bin = get_ffmpeg_binary()
        tempo_filter = f"atempo={speed}" if speed != 1.0 else "anull"
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "s16le",
            "-ar", "24000",
            "-ac", "1",
            "-i", str(raw_pcm_path),
            "-af", tempo_filter,
            "-ar", "44100",
            "-c:a", "pcm_s16le",
            str(out_path)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        if raw_pcm_path.exists():
            raw_pcm_path.unlink()

        with wave.open(str(out_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)

        return duration
