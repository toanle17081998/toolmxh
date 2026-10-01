import asyncio
import subprocess
import re
from pathlib import Path
from typing import Dict, Any
from app.config import get_ffmpeg_binary

class QualityControlValidator:
    """Kiểm tra chất lượng video hoàn thiện (Resolution, Bitrate, Duration, Audio track)."""

    @staticmethod
    async def validate_video(video_path: str, expected_width: int = 1080, expected_height: int = 1920) -> Dict[str, Any]:
        p = Path(video_path)
        if not p.exists():
            return {"valid": False, "error": f"File không tồn tại: {video_path}"}

        file_size_mb = p.stat().st_size / (1024 * 1024)
        cmd = [get_ffmpeg_binary(),'-v','info','-xerror','-i',str(p),'-map','0:v:0','-map','0:a?',
               '-progress','pipe:1','-nostats','-f','null','-']

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(),300)
            except (asyncio.TimeoutError,asyncio.CancelledError):
                if proc.returncode is None:
                    proc.kill()
                await proc.wait()
                raise
            info = stderr.decode('utf-8',errors='replace').split('Stream mapping:')[0]
            has_video,has_audio = 'Video:' in info,'Audio:' in info
            length = re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)',info)
            duration = int(length[1])*3600+int(length[2])*60+float(length[3]) if length else 0
            dimensions = bool(re.search(rf'\b{expected_width}x{expected_height}\b',info))
            frames = re.findall(r'^frame=(\d+)',stdout.decode('utf-8'),re.MULTILINE)

            return {
                "valid": proc.returncode==0 and has_video and has_audio and dimensions and duration>0 and bool(frames) and int(frames[-1])>0,
                "file_size_mb": round(file_size_mb, 2),
                "duration_seconds": round(duration, 2),
                "has_video_stream": has_video,
                "has_audio_stream": has_audio,
                "valid_dimensions":dimensions,
                "decoded_frames":int(frames[-1]) if frames else 0
            }
        except Exception as e:
            return {
                "valid": False,
                "file_size_mb": round(file_size_mb, 2),
                "error":type(e).__name__+': '+str(e)
            }
