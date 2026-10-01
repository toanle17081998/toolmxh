import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


class SimulationVideoRequestTest(unittest.TestCase):
    def test_legacy_request_and_stored_project_default_to_short(self):
        from app.web.server import GenerateRequest
        from app.models.project import ProjectConfig
        request = GenerateRequest(topic='Ocean discoveries')
        self.assertEqual(request.video_type, 'short_content')
        self.assertEqual(ProjectConfig(project_id='legacy', topic='test').video_type, 'short_content')

    def test_simulation_has_no_topic_requirement_and_rejects_unreleased_choices(self):
        from app.web.server import GenerateRequest
        from pydantic import ValidationError
        request = GenerateRequest(video_type='SIMULATION_VIDEO', duration=180, seed=9)
        self.assertEqual(request.simulation_config().aspect_ratio, '16:9')
        self.assertEqual(request.simulation_config().seed, 9)
        for invalid in ({'duration': 0}, {'duration': 600}, {'quality':'invalid'}, {'seed':-1},
                        {'aspect_ratio':'1:1'}, {'vehicle':'brick_monster_truck'}, {'difficulty':9}):
            with self.assertRaises(ValidationError):
                GenerateRequest(video_type='simulation_video', **invalid)
        with self.assertRaises(ValidationError):
            GenerateRequest(topic='  ')

    def test_enqueue_persists_state_and_does_not_render_in_handler(self):
        from fastapi.testclient import TestClient
        from app.web import server
        from app.config import settings
        async def enqueue_test():
            from fastapi import BackgroundTasks
            tasks = BackgroundTasks()
            request = server.GenerateRequest(video_type='simulation_video', duration=30, seed=123)
            result = await server.start_generation(request, tasks)
            self.assertEqual(len(tasks.tasks), 1)
            from app.core.state_manager import ProjectStateManager
            state = ProjectStateManager(result['project_id']).load_state()
            self.assertEqual(state.config.video_type, 'simulation_video')
            self.assertEqual(state.config.simulation.seed, 123)
            server.running_projects.discard(result['project_id'])
        with tempfile.TemporaryDirectory() as root, patch.object(settings, 'PROJECTS_DIR', Path(root)):
            asyncio.run(enqueue_test())

    def test_legacy_dispatch_calls_original_factory(self):
        from app.web import server
        factory = AsyncMock()
        factory.generate_video.return_value = {'final_video_path':'legacy.mp4'}
        with patch.object(server, 'VietnameseVideoFactory', return_value=factory):
            asyncio.run(server.run_factory_task('legacy_dispatch', server.GenerateRequest(topic='test')))
        self.assertEqual(factory.generate_video.await_args.kwargs['topic'], 'test')


class SimulationResumeTest(unittest.IsolatedAsyncioTestCase):
    async def test_failed_segment_resumes_without_rerendering_completed_segment(self):
        from app.config import settings, get_ffmpeg_binary
        from app.simulation.models import SimulationConfig
        from app.simulation.service import SimulationVideoService
        from app.simulation.blender_renderer import run_process
        from app.core.state_manager import ProjectStateManager
        calls = []
        async def render(scenario, segment, directory, width, height):
            calls.append(segment.index)
            if segment.index == 2 and calls.count(2) == 1:
                raise RuntimeError('intentional failure')
            directory.mkdir(parents=True, exist_ok=True)
            output = directory/'output.mp4'
            await run_process([get_ffmpeg_binary(), '-y', '-f', 'lavfi', '-i', f'color=c=blue:s={width}x{height}:r=30:d=2',
                               '-c:v','libx264','-pix_fmt','yuv420p', str(output)], directory/'test.log',30)
            return output
        with tempfile.TemporaryDirectory() as root, patch.object(settings,'PROJECTS_DIR',Path(root)/'projects'), patch.object(settings,'OUTPUTS_DIR',Path(root)/'outputs'), patch.object(settings,'BLENDER_SEGMENT_RETRIES',0):
            renderer = AsyncMock()
            renderer.render_segment.side_effect = render
            service = SimulationVideoService(renderer=renderer)
            config = SimulationConfig(duration=4,segment_seconds=2,quality='draft',seed=3)
            with self.assertRaisesRegex(RuntimeError,'intentional failure'):
                await service.generate_video('resume_test',config)
            state = ProjectStateManager('resume_test').load_state()
            self.assertEqual(state.segments_progress[1].status,'COMPLETED')
            self.assertEqual(state.segments_progress[2].status,'FAILED')
            result = await service.generate_video('resume_test',config)
            self.assertEqual(calls,[1,2,2])
            self.assertTrue(Path(result['final_video_path']).exists())
            state = ProjectStateManager('resume_test').load_state()
            self.assertEqual(state.progress_percentage,100)
            self.assertEqual(state.segments_progress[2].attempts,2)
            self.assertIsNone(state.narration_audio_path)
            self.assertIsNone(state.subtitle_ass_path)
