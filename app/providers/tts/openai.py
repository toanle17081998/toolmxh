import os
import wave
import subprocess
from pathlib import Path
from typing import Optional
from openai import OpenAI
from app.providers.tts.base import TTSProvider
from app.config import settings, get_ffmpeg_binary

class OpenAITTSProvider(TTSProvider):
    """Vietnamese Studio Voice sử dụng OpenAI tts-1-hd với chất giọng đỉnh cao (onyx, nova, shimmer...)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY không được tìm thấy để sử dụng OpenAI TTS HD.")
        self.client = OpenAI(api_key=self.api_key)

    async def synthesize_to_file(
        self,
        text: str,
        output_wav_path: str,
        voice: str = "onyx",
        speed: float = 1.0
    ) -> float:
        out_path = Path(output_wav_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_mp3 = out_path.with_suffix(".temp_openai.mp3")

        # OpenAI voice mapping: onyx (nam trầm ấm), nova (nữ truyền cảm), shimmer (nữ thanh thoát)
        valid_voices = ["onyx", "nova", "shimmer", "alloy", "echo", "fable"]
        v_selected = voice.lower() if voice.lower() in valid_voices else "onyx"

        response = self.client.audio.speech.create(
            model="tts-1-hd",
            voice=v_selected,
            input=text,
            speed=speed
        )
        response.write_to_file(str(temp_mp3))

        # Chuyển đổi sang chuẩn WAV 44.1kHz PCM mono
        ffmpeg_bin = get_ffmpeg_binary()
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(temp_mp3),
            "-af", "highpass=f=70,afade=t=in:ss=0:d=0.06,areverse,afade=t=in:ss=0:d=0.06,areverse",
            "-ar", "44100",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(out_path)
        ]
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if temp_mp3.exists():
            temp_mp3.unlink()

        with wave.open(str(out_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)

        return duration
