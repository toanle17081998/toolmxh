import asyncio
import subprocess
from pathlib import Path
import edge_tts
from app.providers.tts.base import TTSProvider
from app.config import get_ffmpeg_binary

class EdgeTTSProvider(TTSProvider):
    """Vietnamese Neural TTS sử dụng Microsoft Edge (vi-VN-HoaiMyNeural / vi-VN-NamMinhNeural)."""

    async def synthesize_to_file(
        self,
        text: str,
        output_wav_path: str,
        voice: str = "vi-VN-HoaiMyNeural",
        speed: float = 1.0
    ) -> float:
        out_path = Path(output_wav_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_mp3 = out_path.with_suffix(".temp_edge.mp3")

        rate_str = f"+{int((speed - 1.0) * 100)}%" if speed >= 1.0 else f"-{int((1.0 - speed) * 100)}%"
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_str)
        # Timeout 4s để tự động fallback nhanh nếu mạng chặn WSS
        await asyncio.wait_for(communicate.save(str(temp_mp3)), timeout=4.0)

        # Convert sang WAV 44.1kHz PCM
        ffmpeg_bin = get_ffmpeg_binary()
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(temp_mp3),
            "-ar", "44100",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(out_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        await proc.wait()

        if temp_mp3.exists():
            temp_mp3.unlink()

        import wave
        with wave.open(str(out_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)

        return duration
