import asyncio
import re
from pathlib import Path
from app.config import get_ffmpeg_binary


async def validate_media(path, width, height, duration, fps, require_audio=False):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f'Missing or empty video: {path}')
    # Decode the complete video, so truncated or stale cache entries cannot pass.
    process = await asyncio.create_subprocess_exec(
        get_ffmpeg_binary(), '-v', 'info', '-xerror', '-i', str(path), '-map', '0:v:0',
        '-map', '0:a?', '-progress', 'pipe:1', '-nostats', '-f', 'null', '-',
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), 300)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise
    detail = stderr.decode('utf-8', errors='replace')
    frames = re.findall(r'^frame=(\d+)', stdout.decode('utf-8'), re.MULTILINE)
    expected = round(duration * fps)
    has_audio = 'Audio:' in detail
    valid_dimensions = bool(re.search(rf'\b{width}x{height}\b', detail))
    if process.returncode or not frames or int(frames[-1]) != expected or not valid_dimensions or (require_audio and not has_audio):
        raise RuntimeError(f'Invalid video {path}; expected {width}x{height}, {expected} frames, audio={require_audio}\n{detail[-3000:]}')
    return {'valid': True, 'frames': int(frames[-1]), 'width': width, 'height': height,
            'duration': duration, 'has_audio': has_audio, 'file_size_bytes': path.stat().st_size}
