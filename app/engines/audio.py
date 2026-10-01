import asyncio
import math
import subprocess
import numpy as np
from pathlib import Path
from typing import Optional
from app.config import get_ffmpeg_binary

class AudioEngine:
    """Xử lý trộn âm thanh (Narration + BGM) với kỹ thuật Auto-Ducking tự động."""

    async def mix_audio(
        self,
        narration_wav_path: str,
        output_wav_path: str,
        total_duration: float,
        bgm_path: Optional[str] = None
    ) -> str:
        out_p = Path(output_wav_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_bin = get_ffmpeg_binary()

        # 1. Nếu chưa có file BGM, tự động tổng hợp đoạn ambient cinematic pad không bản quyền
        effective_bgm = bgm_path
        temp_bgm = None
        if not effective_bgm or not Path(effective_bgm).exists():
            temp_bgm = out_p.parent / "procedural_ambient_bgm.wav"
            self._generate_ambient_drone(str(temp_bgm), total_duration)
            effective_bgm = str(temp_bgm)

        # 2. Sử dụng FFmpeg amix và volume ducking
        # Giọng đọc ở 1.0, BGM ở 0.15 với fade out 2 giây cuối
        fade_start = max(0.0, total_duration - 2.0)
        filter_complex = (
            f"[1:a]volume=0.15,afade=t=out:st={fade_start:.2f}:d=2.0[bgm];"
            f"[0:a]volume=1.0[voice];"
            f"[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )

        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(narration_wav_path),
            "-i", str(effective_bgm),
            "-filter_complex", filter_complex,
            "-map", "[aout]",
            "-c:a", "pcm_s16le",
            "-ar", "44100",
            str(out_p)
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        await proc.wait()

        if temp_bgm and temp_bgm.exists():
            temp_bgm.unlink()

        return str(out_p)

    def _generate_ambient_drone(self, output_path: str, duration: float) -> None:
        """Tạo đoạn nhạc nền Ambient Drone Cinematic không bản quyền bằng numpy."""
        import wave
        sample_rate = 44100
        num_samples = int(duration * sample_rate)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # Hợp âm sâu lắng (D minor chord: D2, A2, F3) + dao động LFO nhẹ nhàng
        f_d2 = 73.42
        f_a2 = 110.00
        f_f3 = 174.61

        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.2 * t)
        wave_data = (
            0.4 * np.sin(2 * np.pi * f_d2 * t) +
            0.3 * np.sin(2 * np.pi * f_a2 * t + 0.5) +
            0.2 * np.sin(2 * np.pi * f_f3 * t + 1.0)
        ) * (0.8 + 0.2 * lfo)

        # Làm mềm mép đầu và cuối tránh tiếng click
        fade_len = int(sample_rate * 1.0)
        if num_samples > fade_len * 2:
            fade_in = np.linspace(0, 1, fade_len)
            fade_out = np.linspace(1, 0, fade_len)
            wave_data[:fade_len] *= fade_in
            wave_data[-fade_len:] *= fade_out

        scaled = np.int16(wave_data * 32767 * 0.4)
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(scaled.tobytes())
