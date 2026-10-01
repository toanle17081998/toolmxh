import asyncio
import subprocess
from pathlib import Path
from typing import List
from app.config import get_ffmpeg_binary

class VideoComposer:
    """Ghép nối các cảnh video AI, chèn âm thanh hoàn thiện và burn phụ đề bằng FFmpeg."""

    async def compose_video(
        self,
        scene_video_paths: List[str],
        mixed_audio_path: str,
        subtitle_ass_path: str,
        output_mp4_path: str,
        width: int = 1080,
        height: int = 1920,
        burn_subtitles: bool = True
    ) -> str:
        out_p = Path(output_mp4_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_bin = get_ffmpeg_binary()

        # 1. Tạo file concat danh sách scene video
        concat_txt = out_p.parent / "scenes_concat.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for vp in scene_video_paths:
                f.write(f"file '{Path(vp).resolve().as_posix()}'\n")

        # 2. Xử lý đường dẫn subtitle cho FFmpeg filter trên Windows
        # Trong FFmpeg filter, dấu hai chấm và dấu xuyệt ngược cần được escape
        sub_p = Path(subtitle_ass_path).resolve().as_posix()
        # Thay thế C:/ thành C\\:/ để FFmpeg filter không nhầm với filter separator
        sub_filter_path = sub_p.replace(":", "\\:")

        vf_filters = [f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"]
        if burn_subtitles and Path(subtitle_ass_path).exists():
            vf_filters.append(f"ass='{sub_filter_path}'")

        vf_str = ",".join(vf_filters)

        cmd = [
            ffmpeg_bin, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-i", str(mixed_audio_path),
            "-vf", vf_str,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-pix_fmt", "yuv420p",
            str(out_p)
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        await proc.wait()

        if concat_txt.exists():
            concat_txt.unlink()

        if not out_p.exists():
            raise RuntimeError(f"FFmpeg render master video failed: {output_mp4_path}")

        return str(out_p)
