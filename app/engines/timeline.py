import asyncio
import wave
import subprocess
from pathlib import Path
from typing import List
from app.models.script import StructuredScript
from app.models.timeline import AudioTimeline, SceneTiming, WordTimestamp
from app.providers.tts.base import TTSProvider
from app.config import get_ffmpeg_binary

class TimelineEngine:
    """Audio-First Timeline Engine: Giọng đọc quyết định thời lượng chính xác của từng cảnh."""

    def __init__(self, tts_provider: TTSProvider):
        self.tts = tts_provider

    async def build_timeline(
        self,
        script: StructuredScript,
        project_dir: Path,
        voice: str = "vi-VN-HoaiMyNeural"
    ) -> AudioTimeline:
        audio_dir = project_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        scenes_dir = project_dir / "scenes"

        scene_timings: List[SceneTiming] = []
        scene_wav_paths: List[Path] = []
        current_time = 0.0

        for scene in script.scenes:
            scene_folder = scenes_dir / f"{scene.id:03d}"
            scene_folder.mkdir(parents=True, exist_ok=True)
            scene_audio_path = scene_folder / "narration.wav"

            # Sinh audio cho từng cảnh
            duration = await self.tts.synthesize_to_file(
                text=scene.narration,
                output_wav_path=str(scene_audio_path),
                voice=voice
            )

            # Tính toán phân bổ từ cho Karaoke Subtitle
            words = scene.narration.split()
            word_ts: List[WordTimestamp] = []
            if words:
                word_dur = duration / len(words)
                w_start = current_time
                for w in words:
                    word_ts.append(WordTimestamp(
                        word=w,
                        start_time=w_start,
                        end_time=w_start + word_dur
                    ))
                    w_start += word_dur

            scene_timings.append(SceneTiming(
                scene_id=scene.id,
                start_time=current_time,
                end_time=current_time + duration,
                duration=duration,
                narration_audio_path=str(scene_audio_path),
                words=word_ts
            ))

            scene_wav_paths.append(scene_audio_path)
            current_time += duration

        # Ghép toàn bộ các đoạn thoại thành master_narration.wav
        master_audio_path = audio_dir / "master_narration.wav"
        await self._concat_wav_files(scene_wav_paths, master_audio_path)

        return AudioTimeline(
            total_duration=current_time,
            scenes=scene_timings,
            master_narration_path=str(master_audio_path)
        )

    async def _concat_wav_files(self, wav_paths: List[Path], output_path: Path) -> None:
        """Nối danh sách file WAV bằng FFmpeg concat filter."""
        ffmpeg_bin = get_ffmpeg_binary()
        concat_txt = output_path.parent / "audio_concat.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for wp in wav_paths:
                f.write(f"file '{wp.resolve().as_posix()}'\n")

        cmd = [
            ffmpeg_bin, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=9",
            "-c:a", "pcm_s16le",
            "-ar", "44100",
            str(output_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        await proc.wait()
        if concat_txt.exists():
            concat_txt.unlink()
