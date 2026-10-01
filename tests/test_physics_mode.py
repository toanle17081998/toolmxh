import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class PhysicsModeTest(unittest.TestCase):
    def test_corrected_public_config_and_legacy_mode_alias(self):
        from app.web.server import GenerateRequest
        from app.models.project import ProjectConfig
        request = GenerateRequest(video_type='PHYSICS_SIMULATION_VIDEO',simulation_type='brick_vehicle_obstacle',
                                  duration=600,difficulty='progressive',quality='PREVIEW',sound='SFX_ONLY',seed=123456)
        config = request.simulation_config()
        self.assertEqual(config.vehicle,'brick_crawler')
        self.assertEqual(config.dimensions(),(480,270))
        self.assertEqual(config.difficulty,2)
        self.assertEqual(config.sound,'sfx_only')
        self.assertEqual(ProjectConfig(project_id='old',topic='',video_type='simulation_video').video_type,'physics_simulation_video')

    def test_simulation_dispatch_never_constructs_short_factory(self):
        import asyncio
        from unittest.mock import AsyncMock
        from app.web import server
        service = AsyncMock()
        with patch.object(server,'SimulationVideoService',return_value=service), patch.object(server,'VietnameseVideoFactory') as short:
            asyncio.run(server.run_factory_task('physics_dispatch',server.GenerateRequest(video_type='physics_simulation_video',duration=20)))
        short.assert_not_called()
        service.generate_video.assert_awaited_once()


class PhysicsValidationGateTest(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_simulation_does_not_start_render_or_ffmpeg(self):
        import sys
        from app.simulation.models import SimulationConfig
        from app.simulation.scenario import ScenarioGenerator
        from app.simulation.blender_renderer import BlenderSimulationRenderer
        from unittest.mock import AsyncMock
        scenario = ScenarioGenerator().generate(SimulationConfig(duration=20,seed=42))
        runner = AsyncMock(side_effect=RuntimeError('Vehicle stuck'))
        with tempfile.TemporaryDirectory() as root, patch('app.simulation.blender_renderer.run_process',runner):
            with self.assertRaisesRegex(RuntimeError,'Vehicle stuck'):
                await BlenderSimulationRenderer(sys.executable).render_segment(scenario,scenario.segments[0],Path(root),480,270)
        self.assertEqual(runner.await_count,1)
        self.assertNotIn('--playback',runner.await_args.args[0])

    async def test_render_cache_identity_covers_engine_quality_and_segment_slice(self):
        from app.simulation.fingerprint import render_fingerprint
        from app.simulation.models import SimulationConfig
        from app.simulation.scenario import ScenarioGenerator
        scenario = ScenarioGenerator().generate(SimulationConfig(duration=20,segment_seconds=10,seed=42))
        segment = scenario.segments[0]
        base = render_fingerprint('physics',scenario,segment,480,270,'BLENDER_EEVEE_NEXT')
        self.assertNotEqual(base,render_fingerprint('physics',scenario,segment,480,270,'CYCLES'))
        self.assertNotEqual(base,render_fingerprint('physics',scenario,scenario.segments[1],480,270,'BLENDER_EEVEE_NEXT'))
        changed = scenario.model_copy(update={'quality':'high'})
        self.assertNotEqual(base,render_fingerprint('physics',changed,segment,480,270,'BLENDER_EEVEE_NEXT'))
