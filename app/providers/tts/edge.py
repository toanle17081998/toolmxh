import os
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
import edge_tts
from app.providers.tts.base import TTSProvider
from app.config import get_ffmpeg_binary

class EdgeTTSProvider(TTSProvider):
    """Vietnamese Neural TTS sử dụng Microsoft Edge (vi-VN-NamMinhNeural / vi-VN-HoaiMyNeural)."""

    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy or os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or "http://172.16.120.13:3128"

    async def synthesize_to_file(
        self,
        text: str,
        output_wav_path: str,
        voice: str = "vi-VN-NamMinhNeural",
        speed: float = 1.0
    ) -> float:
        out_path = Path(output_wav_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_mp3 = out_path.with_suffix(".temp_edge.mp3")

        rate_str = f"+{int((speed - 1.0) * 100)}%" if speed >= 1.0 else f"-{int((1.0 - speed) * 100)}%"
        
        # Thử nghiệm với các proxy và cơ chế retry kiên cường
        saved = False
        last_error = None
        proxies_to_try = [self.proxy]
        if None not in proxies_to_try:
            proxies_to_try.append(None)

        for attempt in range(4):
            for p in proxies_to_try:
                if temp_mp3.exists():
                    try:
                        temp_mp3.unlink()
                    except Exception:
                        pass
                try:
                    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_str, proxy=p)
                    await asyncio.wait_for(communicate.save(str(temp_mp3)), timeout=20.0)
                    if temp_mp3.exists() and temp_mp3.stat().st_size > 500:
                        saved = True
                        break
                except Exception as e:
                    last_error = e
                    continue
            if saved:
                break
            await asyncio.sleep(1.0 * (attempt + 1))

        if not saved or not temp_mp3.exists() or temp_mp3.stat().st_size == 0:
            raise RuntimeError(f"Edge-TTS failed to synthesize after 4 attempts: {last_error}")

        # Convert sang WAV 44.1kHz PCM kèm bộ lọc Master Studio (Khử tạp âm, lọc dải tần giọng nói, nén động dynamic compressor và chuẩn hóa âm lượng -16 LUFS)
        ffmpeg_bin = get_ffmpeg_binary()
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(temp_mp3),
            "-af", "highpass=f=60,lowpass=f=12000,acompressor=threshold=-18dB:ratio=3:attack=5:release=50,loudnorm=I=-16:TP=-1.5:LRA=9",
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
            try:
                temp_mp3.unlink()
            except Exception:
                pass

        import wave
        with wave.open(str(out_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)

        return duration

