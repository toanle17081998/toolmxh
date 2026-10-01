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
    input_metadata = detail.split('Stream mapping:')[0]
    has_audio = 'Audio:' in input_metadata
    valid_dimensions = bool(re.search(rf'\b{width}x{height}\b', input_metadata))
    rate = re.search(r'(\d+(?:\.\d+)?) fps',input_metadata)
    length = re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)',input_metadata)
    actual_duration = int(length[1])*3600+int(length[2])*60+float(length[3]) if length else -1
    valid_timing = rate and abs(float(rate[1])-fps)<.01 and abs(actual_duration-duration)<=max(.08,2/fps)
    if process.returncode or not frames or int(frames[-1]) != expected or not valid_dimensions or not valid_timing or (require_audio and not has_audio):
        raise RuntimeError(f'Invalid video {path}; expected {width}x{height}, {expected} frames, audio={require_audio}\n{detail[-3000:]}')
    return {'valid': True, 'frames': int(frames[-1]), 'width': width, 'height': height,
            'duration': actual_duration, 'fps':fps, 'has_audio': has_audio, 'file_size_bytes': path.stat().st_size}
