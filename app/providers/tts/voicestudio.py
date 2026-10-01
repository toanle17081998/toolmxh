import os
import aiohttp
import wave
import subprocess
from pathlib import Path
from typing import Optional
from app.providers.tts.base import TTSProvider
from app.config import get_ffmpeg_binary

class VoiceStudioProvider(TTSProvider):
    """Tích hợp VoiceStudio (debpalash/VoiceStudio) - Nền tảng Local ElevenLabs Alternative 16+ Engine:
    Hỗ trợ CosyVoice 2/3, Kokoro, F5-TTS, GPT-SoVITS và Zero-shot Voice Cloning từ file audio mẫu."""

    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        self.api_url = api_url.rstrip("/")

    async def synthesize_to_file(
        self,
        text: str,
        output_wav_path: str,
        voice: str = "cosyvoice",
        speed: float = 1.0,
        clone_reference_wav: Optional[str] = None
    ) -> float:
        out_path = Path(output_wav_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_audio = out_path.with_suffix(".temp_voicestudio.wav")

        payload = {
            "text": text,
            "engine": voice,
            "speed": speed,
            "language": "vi"
        }
        if clone_reference_wav and Path(clone_reference_wav).exists():
            payload["reference_audio"] = str(Path(clone_reference_wav).resolve())

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/api/tts/synthesize", json=payload, timeout=60) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"VoiceStudio API error ({resp.status}): {error_text}")
                audio_bytes = await resp.read()

        with open(temp_audio, "wb") as f:
            f.write(audio_bytes)

        # Chuẩn hóa về WAV 44.1kHz PCM mono
        ffmpeg_bin = get_ffmpeg_binary()
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(temp_audio),
            "-ar", "44100",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(out_path)
        ]
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if temp_audio.exists():
            temp_audio.unlink()

        with wave.open(str(out_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)

        return duration
