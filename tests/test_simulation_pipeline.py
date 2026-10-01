import asyncio
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch


class BlenderRendererTest(unittest.IsolatedAsyncioTestCase):
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


class SimulationCompositionTest(unittest.IsolatedAsyncioTestCase):
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
            await VideoComposer().compose_simulation(segments, str(root/'mix.wav'), str(final), 2)
            result = await validate_media(final, 160, 90, 2, 30, require_audio=True)
            self.assertTrue(result['valid'])
            self.assertEqual(result['frames'], 60)
