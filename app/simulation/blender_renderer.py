import asyncio
import json
import logging
import shutil
import time
import weakref
import uuid
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

    def fingerprint(self, scenario, experiment_id=None):
        from app.simulation.fingerprint import physics_fingerprint
        return physics_fingerprint(scenario,self.check_available(),experiment_id)

    def render_fingerprint(self,scenario,segment,width,height):
        from app.simulation.fingerprint import render_fingerprint
        return render_fingerprint(self.fingerprint(scenario,segment.experiment_id),scenario,segment,width,height,settings.BLENDER_RENDER_ENGINE)

    async def render_segment(self, scenario, segment, directory, width, height):
        binary = self.check_available()
        directory = Path(directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        attempt_dir = directory/'attempts'/uuid.uuid4().hex
        attempt_dir.mkdir(parents=True)
        fingerprint = self.fingerprint(scenario,segment.experiment_id)
        payload = {'scenario': scenario.model_dump(), 'segment': segment.model_dump(), 'width': width, 'height': height,
                   'fingerprint':fingerprint,
                   'engine': settings.BLENDER_RENDER_ENGINE, 'output_dir': str(attempt_dir)}
        if segment.experiment_id is not None:
            payload['experiment'] = next(trial.model_dump() for trial in scenario.experiments if trial.id==segment.experiment_id)
        scenario_path = attempt_dir / 'scenario.json'
        scenario_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        shutil.copyfile(scenario_path,directory/'scenario.json')
        loop = asyncio.get_running_loop()
        if loop not in _render_limits:
            _render_limits[loop] = asyncio.Semaphore(settings.BLENDER_MAX_PARALLEL_JOBS)
        started = time.monotonic()
        async with _render_limits[loop]:
            # Private attempts isolate even an orphan Blender left by a killed worker.
            frames = attempt_dir / 'frames'
            frames.mkdir(exist_ok=True)
            if scenario.physics:
                script = Path(__file__).with_name('experiment_scene.py' if segment.experiment_id is not None else 'physics_scene.py')
                cache_root = directory.parent if directory.parent.name=='segments' else directory
                cache = cache_root/'_physics_cache'/fingerprint/'telemetry.json'
                # Simulate/validate without rendering, then replay in a fresh process.
                cache_valid = False
                if cache.exists():
                    try:
                        cached_telemetry = json.loads(cache.read_text(encoding='utf-8'))
                        expected = payload['experiment']['frame_count'] if 'experiment' in payload else scenario.duration*scenario.fps
                        cache_valid = cached_telemetry.get('validated') and cached_telemetry.get('fingerprint')==fingerprint and len(cached_telemetry.get('samples',[]))==expected
                    except (ValueError,OSError):
                        cache_valid = False
                if cache_valid:
                    shutil.copyfile(cache,attempt_dir/'telemetry.json')
                else:
                    await run_process([binary,'--background','--factory-startup','--python-exit-code','1',
                                       '--python',script,'--',scenario_path],attempt_dir/'physics.log',settings.BLENDER_TIMEOUT)
                    cache.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(attempt_dir/'telemetry.json',cache)
                await run_process([binary,'--background','--factory-startup','--python-exit-code','1',
                                   '--python',script,'--','--playback',scenario_path],attempt_dir/'blender.log',settings.BLENDER_TIMEOUT)
                shutil.copyfile(attempt_dir/'telemetry.json',directory/'telemetry.json')
            else:
                raise RuntimeError('Legacy animated scenarios must be replanned before physics rendering')
        render_time = time.monotonic() - started
        if len(list(frames.glob('*.png'))) != segment.frame_count:
            raise RuntimeError(f'Blender produced incomplete frames; see {attempt_dir / "blender.log"}')
        temporary = attempt_dir / 'output.partial.mp4'
        ffmpeg_started = time.monotonic()
        await run_process([get_ffmpeg_binary(), '-y', '-framerate', scenario.fps, '-start_number', '1',
                           '-i', frames / '%06d.png', '-frames:v', segment.frame_count, '-an', '-c:v', 'libx264',
                           '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', temporary],
                          attempt_dir / 'ffmpeg.log', settings.BLENDER_TIMEOUT)
        from app.simulation.media import validate_media
        await validate_media(temporary, width, height, segment.frame_count / scenario.fps, scenario.fps)
        output = directory / 'output.mp4'
        temporary.replace(output)
        # Keep a representative image independently of optional frame cleanup.
        shutil.copyfile(frames / '000001.png', directory / 'preview.png')
        for filename in ('blender.log','ffmpeg.log','scene.blend'):
            shutil.copyfile(attempt_dir/filename,directory/filename)
        logger.info('segment=%s seed=%s duration=%.2f obstacles=%s blender_seconds=%.2f ffmpeg_seconds=%.2f',
                    segment.index, segment.seed, segment.frame_count / scenario.fps,
                    [s.type for s in segment.sections], render_time, time.monotonic() - ffmpeg_started)
        (directory / 'timing.json').write_text(json.dumps({'blender_seconds': render_time,
                                                        'fingerprint':self.render_fingerprint(scenario,segment,width,height),
                                                        'physics_fingerprint':fingerprint,
                                                       'ffmpeg_seconds': time.monotonic() - ffmpeg_started}), encoding='utf-8')
        return output


BlenderSimulationRenderer = BlenderRenderer
