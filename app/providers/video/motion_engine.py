import asyncio
import subprocess
from pathlib import Path
from app.providers.video.base import GenerativeVideoProvider
from app.config import get_ffmpeg_binary

class CinematicMotionVideoEngine(GenerativeVideoProvider):
    """Engine chuyển đổi ảnh AI tham chiếu thành video điện ảnh mượt mà (Image-to-Video).
    Áp dụng các chuyển động máy quay vật lý thực (Pan, Zoom, Tilt, Orbit) với thời lượng khớp chính xác 100% audio."""

    async def generate_image_to_video(
        self,
        image_path: str,
        prompt: str,
        output_path: str,
        duration_seconds: float,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1
    ) -> str:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img_p = Path(image_path)
        if not img_p.exists():
            raise FileNotFoundError(f"Reference image not found: {image_path}")

        fps = 30
        total_frames = max(30, int(round(duration_seconds * fps)))
        p_lower = prompt.lower()

        # Xây dựng bộ lọc camera motion tương ứng với prompt của kịch bản
        if any(w in p_lower for w in ["pull back", "zoom out", "crane pull"]):
            # Zoom out mượt mà từ 1.25 về 1.0
            zoom_expr = f"'1.25-0.25*on/{total_frames}'"
            x_expr = "'(iw-iw/zoom)/2'"
            y_expr = "'(ih-ih/zoom)/2'"
        elif any(w in p_lower for w in ["pan left", "sweeping pan"]):
            # Di chuyển góc quay sang trái
            zoom_expr = "'1.15'"
            x_expr = f"'(iw-iw/zoom)*(1-on/{total_frames})'"
            y_expr = "'(ih-ih/zoom)/2'"
        elif any(w in p_lower for w in ["pan right", "tracking"]):
            # Di chuyển góc quay sang phải
            zoom_expr = "'1.15'"
            x_expr = f"'(iw-iw/zoom)*(on/{total_frames})'"
            y_expr = "'(ih-ih/zoom)/2'"
        elif any(w in p_lower for w in ["tilt down", "crane down"]):
            # Quét máy quay từ trên xuống dưới
            zoom_expr = "'1.15'"
            x_expr = "'(iw-iw/zoom)/2'"
            y_expr = f"'(ih-ih/zoom)*(on/{total_frames})'"
        else:
            # Mặc định: Push in / Slow Zoom In điện ảnh
            zoom_expr = f"'min(1.0+0.25*(on/{total_frames}), 1.25)'"
            x_expr = "'(iw-iw/zoom)/2'"
            y_expr = "'(ih-ih/zoom)/2'"

        # Tạo chuỗi filter zoompan
        vf_filter = (
            f"zoompan=z={zoom_expr}:x={x_expr}:y={y_expr}:"
            f"d={total_frames}:s={width}x{height}:fps={fps},"
            f"format=yuv420p"
        )

        ffmpeg_bin = get_ffmpeg_binary()
        cmd = [
            ffmpeg_bin, "-y",
            "-loop", "1",
            "-i", str(img_p),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-t", f"{duration_seconds:.3f}",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "18",
            str(out_path)
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        await proc.wait()

        if not out_path.exists():
            raise RuntimeError(f"FFmpeg failed to create scene video: {output_path}")

        return str(out_path)

    async def generate_text_to_video(
        self,
        prompt: str,
        output_path: str,
        duration_seconds: float,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1
    ) -> str:
        # Fallback T2V qua quy trình chuẩn: T2I -> I2V
        raise NotImplementedError("Sử dụng luồng T2I -> I2V qua generate_image_to_video để đảm bảo nhất quán visual.")
