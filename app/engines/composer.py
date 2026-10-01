import asyncio
import subprocess
from pathlib import Path
from typing import List
from app.config import get_ffmpeg_binary

class VideoComposer:
    """Ghép nối các cảnh video AI, chèn âm thanh hoàn thiện và burn phụ đề bằng FFmpeg."""

    async def compose_simulation(self, segment_paths: List[str], audio_path: str,
                                 output_path: str, duration: float) -> str:
        from app.simulation.blender_renderer import run_process
        from app.config import settings
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        concat = out.parent / 'segments_concat.txt'
        concat.write_text(''.join("file '" + Path(p).resolve().as_posix().replace("'", "'\\''") + "'\n" for p in segment_paths), encoding='utf-8')
        temporary = out.with_name(out.stem + '.partial.mp4')
        await run_process([get_ffmpeg_binary(), '-y', '-f', 'concat', '-safe', '0', '-i', concat,
                           '-i', audio_path, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy',
                           '-c:a', 'aac', '-b:a', '192k', '-t', duration, '-movflags', '+faststart', temporary],
                          out.parent / 'composition.log', settings.BLENDER_TIMEOUT)
        temporary.replace(out)
        return str(out)

    async def compose_video(
        self,
        scene_video_paths: List[str],
        mixed_audio_path: str,
        subtitle_ass_path: str,
        output_mp4_path: str,
        width: int = 1080,
        height: int = 1920,
        burn_subtitles: bool = True,
        total_duration: float = 0.0
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
        
        # Thêm hiệu ứng Intro Fade-in mở màn điện ảnh và Outro Fade-out kết thúc êm ái
        if total_duration > 3.0:
            fade_out_st = max(0.0, total_duration - 1.2)
            vf_filters.append("fade=t=in:st=0:d=0.8")
            vf_filters.append(f"fade=t=out:st={fade_out_st:.2f}:d=1.2")

        if burn_subtitles and Path(subtitle_ass_path).exists():
            vf_filters.append(f"ass='{sub_filter_path}'")

        vf_str = ",".join(vf_filters)

        cmd = [
            ffmpeg_bin, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-i", str(mixed_audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
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
