import tempfile
import unittest
import wave
from pathlib import Path


class ShortCompositionTest(unittest.IsolatedAsyncioTestCase):
    async def test_failed_composition_preserves_previous_master(self):
        from app.engines.composer import VideoComposer
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            master = root/'master.mp4'
            master.write_bytes(b'previous artifact must not be overwritten on failure')
            before = master.read_bytes()
            with self.assertRaises(RuntimeError):
                await VideoComposer().compose_video([str(root/'missing.mp4')],str(root/'missing.wav'),
                    str(root/'none.ass'),str(master),width=160,height=90,burn_subtitles=False,total_duration=2)
            self.assertEqual(master.read_bytes(),before)

    async def test_actual_short_composition_decodes_with_audio_and_correct_dimensions(self):
        from app.config import get_ffmpeg_binary
        from app.simulation.blender_renderer import run_process
        from app.engines.composer import VideoComposer
        from app.qc.validator import QualityControlValidator
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'scene.mp4'
            await run_process([get_ffmpeg_binary(),'-y','-f','lavfi','-i','color=c=blue:s=160x90:r=30:d=2',
                               '-c:v','libx264','-pix_fmt','yuv420p',source],root/'encode.log',30)
            audio = root/'voice.wav'
            with wave.open(str(audio),'wb') as wav:
                wav.setparams((1,2,44100,0,'NONE','not compressed'))
                wav.writeframes(b'\0\0'*88200)
            output = root/'master.mp4'
            await VideoComposer().compose_video([str(source)],str(audio),str(root/'none.ass'),str(output),
                                                width=160,height=90,burn_subtitles=False,total_duration=2)
            qc = await QualityControlValidator.validate_video(str(output),160,90)
            self.assertTrue(qc['valid'])
            self.assertTrue(qc['has_audio_stream'])
            self.assertEqual(qc['decoded_frames'],60)
            self.assertFalse((await QualityControlValidator.validate_video(str(output),320,180))['valid'])

    async def test_large_corrupt_file_cannot_pass_qc_without_ffprobe(self):
        from app.qc.validator import QualityControlValidator
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'corrupt.mp4'
            path.write_bytes(b'not a video'*100000)
            self.assertFalse((await QualityControlValidator.validate_video(str(path),160,90))['valid'])
