import asyncio
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch


class BlenderRendererTest(unittest.IsolatedAsyncioTestCase):
    async def test_retry_uses_private_workdir_and_does_not_touch_other_attempt_files(self):
        import json
        import sys
        from PIL import Image
        from app.simulation.models import SimulationConfig
        from app.simulation.scenario import ScenarioGenerator
        from app.simulation.blender_renderer import BlenderRenderer, run_process
        scenario = ScenarioGenerator().generate(SimulationConfig(duration=1,seed=42))
        segment = scenario.segments[0]
        segment.frame_count=1
        attempts=[]
        async def render_boundary(command,log_path,timeout):
            if '--background' not in command:
                return await run_process(command,log_path,timeout)
            payload=json.loads(Path(command[-1]).read_text())
            work=Path(payload['output_dir'])
            if '--playback' not in command:
                (work/'telemetry.json').write_text(json.dumps({'validated':True,'fingerprint':payload['fingerprint'],'samples':[]}))
                Path(log_path).write_text('validated physics before render')
                return
            attempts.append(work)
            Image.new('RGB',(160,90),'red').save(work/'frames'/'000001.png')
            (work/'scene.blend').write_bytes(b'unit render boundary')
            Path(log_path).write_text('test renderer log')
        with tempfile.TemporaryDirectory() as directory:
            renderer=BlenderRenderer(binary=sys.executable)
            with patch('app.simulation.blender_renderer.run_process',side_effect=render_boundary):
                await renderer.render_segment(scenario,segment,Path(directory),160,90)
                sentinel=attempts[0]/'frames'/'orphan.png'
                sentinel.write_bytes(b'an orphan still owns this attempt')
                await renderer.render_segment(scenario,segment,Path(directory),160,90)
            self.assertNotEqual(attempts[0],attempts[1])
            self.assertTrue(sentinel.exists())
            self.assertTrue((Path(directory)/'output.mp4').exists())

    async def test_missing_executable_is_explicit(self):
        from app.simulation.blender_renderer import BlenderRenderer
        with self.assertRaisesRegex(RuntimeError, 'BLENDER_PATH'):
            BlenderRenderer(binary='missing-blender-executable').check_available()

    async def test_subprocess_error_and_timeout_leave_logs(self):
        import sys
        from app.simulation.blender_renderer import run_process
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'error.log'
            with self.assertRaisesRegex(RuntimeError, 'failure marker'):
                await run_process([sys.executable, '-c', "import sys; print('failure marker', file=sys.stderr); sys.exit(9)"], log, 10)
            self.assertIn('failure marker', log.read_text())
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                await run_process([sys.executable, '-c', 'import time; time.sleep(5)'], log, .1)

    async def test_corrupt_mp4_is_not_a_valid_cache(self):
        from app.simulation.media import validate_media
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / 'bad.mp4'
            bad.write_bytes(b'not a video')
            with self.assertRaises(RuntimeError):
                await validate_media(bad, 480, 270, 1, 30)


class SimulationAudioTest(unittest.TestCase):
    def test_audio_disabled_is_silence_and_enabled_has_samples(self):
        import numpy as np
        from app.simulation.audio import SimulationAudioManager
        from app.simulation.models import SimulationConfig
        from app.simulation.scenario import ScenarioGenerator
        with tempfile.TemporaryDirectory() as directory:
            for enabled in (False, True):
                scenario = ScenarioGenerator().generate(SimulationConfig(duration=2, seed=4, music=enabled, sound_effects=enabled, engine_sound=enabled))
                output = Path(directory) / 'audio.wav'
                SimulationAudioManager().generate(scenario, output)
                with wave.open(str(output)) as wav:
                    self.assertEqual(wav.getnframes(), 44100 * 2)
                    samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2')
                self.assertEqual(bool(np.any(samples)), enabled)


class SimulationAudioCancellationTest(unittest.IsolatedAsyncioTestCase):
    async def test_cancellation_waits_for_audio_writer_before_releasing_project(self):
        import threading
        import time
        from app.simulation.audio import SimulationAudioManager
        started, finished = threading.Event(), threading.Event()
        def slow_audio(*args):
            started.set()
            time.sleep(.15)
            finished.set()
        manager = SimulationAudioManager()
        with patch.object(manager,'generate',side_effect=slow_audio):
            task = asyncio.create_task(manager.generate_async(None,Path('unused.wav')))
            while not started.is_set():
                await asyncio.sleep(.01)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(finished.is_set())


class SimulationCompositionTest(unittest.IsolatedAsyncioTestCase):
    async def test_media_validation_rejects_wrong_fps_and_duration_even_with_correct_frame_count(self):
        from app.config import get_ffmpeg_binary
        from app.simulation.blender_renderer import run_process
        from app.simulation.media import validate_media
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root/'wrong_fps.mp4'
            await run_process([get_ffmpeg_binary(),'-y','-f','lavfi','-i','color=s=160x90:r=15:d=2',
                               '-c:v','libx264','-pix_fmt','yuv420p',str(video)],root/'encode.log',30)
            with self.assertRaises(RuntimeError):
                await validate_media(video,160,90,1,30)

    async def test_real_ffmpeg_concat_has_exact_frames_audio_and_dimensions(self):
        from app.config import get_ffmpeg_binary
        from app.simulation.blender_renderer import run_process
        from app.simulation.media import validate_media
        from app.engines.composer import VideoComposer
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            segments = []
            for i in range(2):
                video = root / f'{i}.mp4'
                await run_process([get_ffmpeg_binary(), '-y', '-f', 'lavfi', '-i', 'color=c=red:s=160x90:r=30:d=1', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(video)], root / 'ffmpeg.log', 30)
                segments.append(str(video))
            with wave.open(str(root/'mix.wav'), 'wb') as wav:
                wav.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
                wav.writeframes(b'\0\0' * 88200)
            final = root / 'final.mp4'
            composition_attempts=[]
            async def track_composition(command,log,timeout):
                composition_attempts.append((command[-1],command[command.index('-i')+1],log))
                await run_process(command,log,timeout)
            with patch('app.simulation.blender_renderer.run_process',side_effect=track_composition):
                await VideoComposer().compose_simulation(segments, str(root/'mix.wav'), str(final), 2)
                await VideoComposer().compose_simulation(segments, str(root/'mix.wav'), str(final), 2)
            self.assertNotEqual(composition_attempts[0],composition_attempts[1])
            result = await validate_media(final, 160, 90, 2, 30, require_audio=True)
            self.assertTrue(result['valid'])
            self.assertEqual(result['frames'], 60)
