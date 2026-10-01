import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch


class SimulationVideoRequestTest(unittest.TestCase):
    def test_regeneration_holds_ownership_even_if_earlier_running_probe_was_stale(self):
        from app.web import server
        from app.config import settings
        from app.simulation.models import SimulationConfig, SegmentProgress
        from app.simulation.service import prepare_simulation_project
        from app.simulation.lock import ProjectLease
        from fastapi import BackgroundTasks, HTTPException
        async def check():
            manager,state = prepare_simulation_project('race_test',SimulationConfig(duration=30,seed=3))
            state.segments_progress[1] = SegmentProgress(segment_id=1,seed=3,duration=30,status='COMPLETED')
            manager.save_state(state)
            before = manager.state_file.read_text()
            with ProjectLease(manager.project_dir), patch.object(server,'project_is_running',return_value=False):
                with self.assertRaises(HTTPException) as failure:
                    await server.regenerate_scene('race_test',1,BackgroundTasks())
                self.assertEqual(failure.exception.status_code,409)
                self.assertEqual(manager.state_file.read_text(),before)
        with tempfile.TemporaryDirectory() as root, patch.object(settings,'PROJECTS_DIR',Path(root)):
            asyncio.run(check())

    def test_simulation_web_failure_does_not_overwrite_new_owner_state(self):
        from app.web import server
        from app.config import settings
        from app.simulation.models import SimulationConfig
        from app.simulation.service import prepare_simulation_project
        from app.models.project import PipelineStage
        async def check():
            manager,state = prepare_simulation_project('failure_race',SimulationConfig(duration=30,seed=3))
            state.stage=PipelineStage.SIMULATION_RENDERING
            state.progress_message='New CLI owner is rendering'
            manager.save_state(state)
            service = Mock()
            service.generate_video = AsyncMock(side_effect=RuntimeError('old web attempt failed'))
            with patch.object(server,'SimulationVideoService',return_value=service):
                await server.run_factory_task('failure_race',server.GenerateRequest(video_type='simulation_video',duration=30))
            self.assertEqual(manager.load_state().stage,PipelineStage.SIMULATION_RENDERING)
            self.assertEqual(manager.load_state().progress_message,'New CLI owner is rendering')
        with tempfile.TemporaryDirectory() as root, patch.object(settings,'PROJECTS_DIR',Path(root)):
            asyncio.run(check())

    def test_failed_atomic_state_replace_preserves_previous_json(self):
        from app.core.state_manager import ProjectStateManager
        from app.models.project import ProjectConfig
        from app.config import settings
        with tempfile.TemporaryDirectory() as root, patch.object(settings,'PROJECTS_DIR',Path(root)):
            manager = ProjectStateManager('atomic_test')
            state = manager.init_project_structure(ProjectConfig(project_id='atomic_test',topic='test'))
            original = manager.state_file.read_text(encoding='utf-8')
            state.progress_percentage=75
            with patch.object(Path,'replace',side_effect=PermissionError('replacement denied')):
                with self.assertRaises(PermissionError):
                    manager.save_state(state)
            self.assertEqual(manager.state_file.read_text(encoding='utf-8'),original)

    def test_progress_reports_inactive_after_restart_and_resume_rejects_duplicate_job(self):
        from app.web import server
        from app.config import settings
        from app.simulation.models import SimulationConfig
        from app.simulation.service import prepare_simulation_project
        from app.models.project import PipelineStage
        from fastapi import BackgroundTasks, HTTPException
        async def check():
            manager, state = prepare_simulation_project('restart_test',SimulationConfig(duration=30,seed=4))
            state.stage=PipelineStage.SIMULATION_RENDERING
            manager.save_state(state)
            data = await server.get_progress('restart_test')
            self.assertFalse(data['is_running'])
            tasks = BackgroundTasks()
            result = await server.resume_simulation('restart_test',tasks)
            self.assertEqual(result['status'],'RESUMING')
            self.assertEqual(len(tasks.tasks),1)
            self.assertTrue((await server.get_progress('restart_test'))['is_running'])
            with self.assertRaises(HTTPException) as error:
                await server.resume_simulation('restart_test',BackgroundTasks())
            self.assertEqual(error.exception.status_code,409)
            server.running_projects.discard('restart_test')
        with tempfile.TemporaryDirectory() as root, patch.object(settings,'PROJECTS_DIR',Path(root)):
            asyncio.run(check())

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
        for invalid in ({'duration': 0}, {'duration': 1801}, {'quality':'invalid'}, {'seed':-1},
                        {'aspect_ratio':'1:1'}, {'vehicle':'brick_monster_truck'}, {'difficulty':9}):
            with self.assertRaises(ValidationError):
                GenerateRequest(video_type='simulation_video', **invalid)
        with self.assertRaises(ValidationError):
            GenerateRequest(topic='  ')

    def test_enqueue_persists_state_and_does_not_render_in_handler(self):
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
            self.assertEqual(state.config.video_type, 'physics_simulation_video')
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
    async def test_http_creation_validation_progress_and_existing_download_route(self):
        import httpx
        from app.web import server
        from app.config import settings
        with tempfile.TemporaryDirectory() as root, patch.object(settings,'PROJECTS_DIR',Path(root)/'projects'), patch.object(settings,'OUTPUTS_DIR',Path(root)/'outputs'), patch.object(server,'run_factory_task',new=AsyncMock()):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
                invalid = await client.post('/api/generate',json={'video_type':'simulation_video','duration':1801})
                self.assertEqual(invalid.status_code,422)
                created = await client.post('/api/generate',json={'video_type':'simulation_video','duration':30,'seed':7})
                self.assertEqual(created.status_code,200)
                project = created.json()['project_id']
                progress = (await client.get(f'/api/progress/{project}')).json()
                self.assertEqual(progress['config']['video_type'],'physics_simulation_video')
                export = settings.OUTPUTS_DIR/project
                export.mkdir(parents=True)
                (export/'final.mp4').write_bytes(b'download route test')
                downloaded = await client.get(f'/media/{project}/artifact/final.mp4')
                self.assertEqual(downloaded.status_code,200)
                self.assertEqual(downloaded.content,b'download route test')
                self.assertIn('final.mp4',downloaded.headers['content-disposition'])
                self.assertEqual((await client.get(f'/media/{project}/artifact/not_allowed.txt')).status_code,403)
                server.running_projects.discard(project)

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
            from app.simulation.blender_renderer import BlenderRenderer
            renderer = Mock(spec=BlenderRenderer)
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
