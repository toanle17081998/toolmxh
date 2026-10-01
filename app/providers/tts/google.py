import asyncio
import subprocess
from pathlib import Path
from gtts import gTTS
from app.providers.tts.base import TTSProvider
from app.config import get_ffmpeg_binary

class GoogleTTSProvider(TTSProvider):
    """Vietnamese Neural TTS sử dụng Google Translate Engine (miễn phí, siêu ổn định qua mọi mạng/proxy)."""

    async def synthesize_to_file(
        self,
        text: str,
        output_wav_path: str,
        voice: str = "vi",
        speed: float = 1.0
    ) -> float:
        out_path = Path(output_wav_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_mp3 = out_path.with_suffix(".temp.mp3")

        # 1. Chạy gTTS trong thread pool
        def _generate():
            tts = gTTS(text=text, lang="vi", slow=False)
            tts.save(str(temp_mp3))

        await asyncio.to_thread(_generate)

        # 2. Dùng FFmpeg convert sang chuẩn WAV PCM 16-bit 44.1kHz mono và khử 100% tiếng click/rè tivi ở 2 đầu
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
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        await proc.wait()

        if temp_mp3.exists():
            temp_mp3.unlink()

        # 3. Đo chính xác thời lượng file WAV
        import wave
        with wave.open(str(out_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)

        return duration
