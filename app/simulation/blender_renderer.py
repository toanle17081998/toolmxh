import asyncio
import json
import logging
import shutil
import time
import weakref
from pathlib import Path
from app.config import settings, get_ffmpeg_binary

logger = logging.getLogger(__name__)
_render_limits = weakref.WeakKeyDictionary()


async def run_process(command, log_path, timeout):
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('wb') as log:
        process = await asyncio.create_subprocess_exec(*map(str, command), stdout=log, stderr=asyncio.subprocess.STDOUT)
        try:
            await asyncio.wait_for(process.wait(), timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError) as error:
            if process.returncode is None:
                process.kill()
            await process.wait()
            if isinstance(error, asyncio.CancelledError):
                raise
            raise RuntimeError(f'Process timed out after {timeout}s; logs: {log_path}') from error
    if process.returncode != 0:
        with log_path.open('rb') as log:
            log.seek(max(0, log_path.stat().st_size - 8000))
            detail = log.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Process exited {process.returncode}; logs: {log_path}\n{detail}')


class BlenderRenderer:
    def __init__(self, binary=None):
        self.binary = binary or settings.BLENDER_PATH or 'blender'

    def check_available(self):
        binary = shutil.which(self.binary)
        if not binary:
            raise RuntimeError('Blender executable not found. Set BLENDER_PATH to an installed Blender 4.5 executable.')
        return binary

    async def render_segment(self, scenario, segment, directory, width, height):
        binary = self.check_available()
        directory = Path(directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        payload = {'scenario': scenario.model_dump(), 'segment': segment.model_dump(), 'width': width, 'height': height,
                   'engine': settings.BLENDER_RENDER_ENGINE, 'output_dir': str(directory)}
        scenario_path = directory / 'scenario.json'
        scenario_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        loop = asyncio.get_running_loop()
        if loop not in _render_limits:
            _render_limits[loop] = asyncio.Semaphore(settings.BLENDER_MAX_PARALLEL_JOBS)
        started = time.monotonic()
        async with _render_limits[loop]:
            # Clear stale frames on retry; keep logs and scene for debugging failed work.
            frames = directory / 'frames'
            frames.mkdir(exist_ok=True)
            for image in frames.glob('*.png'):
                image.unlink()
            await run_process([binary, '--background', '--factory-startup', '--python-exit-code', '1',
                               '--python', Path(__file__).with_name('blender_scene.py'), '--', scenario_path],
                              directory / 'blender.log', settings.BLENDER_TIMEOUT)
        render_time = time.monotonic() - started
        if len(list(frames.glob('*.png'))) != segment.frame_count:
            raise RuntimeError(f'Blender produced incomplete frames; see {directory / "blender.log"}')
        temporary = directory / 'output.partial.mp4'
        ffmpeg_started = time.monotonic()
        await run_process([get_ffmpeg_binary(), '-y', '-framerate', scenario.fps, '-start_number', '1',
                           '-i', frames / '%06d.png', '-frames:v', segment.frame_count, '-an', '-c:v', 'libx264',
                           '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', temporary],
                          directory / 'ffmpeg.log', settings.BLENDER_TIMEOUT)
        from app.simulation.media import validate_media
        await validate_media(temporary, width, height, segment.frame_count / scenario.fps, scenario.fps)
        output = directory / 'output.mp4'
        temporary.replace(output)
        # Keep a representative image independently of optional frame cleanup.
        shutil.copyfile(frames / '000001.png', directory / 'preview.png')
        logger.info('segment=%s seed=%s duration=%.2f obstacles=%s blender_seconds=%.2f ffmpeg_seconds=%.2f',
                    segment.index, segment.seed, segment.frame_count / scenario.fps,
                    [s.type for s in segment.sections], render_time, time.monotonic() - ffmpeg_started)
        (directory / 'timing.json').write_text(json.dumps({'blender_seconds': render_time,
                                                       'ffmpeg_seconds': time.monotonic() - ffmpeg_started}), encoding='utf-8')
        return output
