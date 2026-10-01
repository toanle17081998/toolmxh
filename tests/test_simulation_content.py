import unittest


class ContentPlanningTest(unittest.TestCase):
    def test_catalog_separates_ideas_from_renderers_and_auto_ideas_are_diverse(self):
        from app.simulation.content import FAMILIES, SimulationIdeaGenerator
        catalog = {family.id:family.public() for family in FAMILIES}
        self.assertEqual(len(catalog),17)
        self.assertFalse(catalog['mechanisms']['renderable'])
        self.assertFalse(catalog['budget_build']['renderable'])
        generator = SimulationIdeaGenerator()
        first = generator.generate(42,count=12)
        self.assertEqual(first,generator.generate(42,count=12))
        self.assertEqual(len({idea['content_type'] for idea in first}),12)
        self.assertTrue(all(idea['renderable'] for idea in first))
        second = generator.generate(42,count=3,history=[idea['id'] for idea in first])
        self.assertFalse(set(idea['id'] for idea in first)&set(idea['id'] for idea in second))

    def test_unavailable_mismatched_and_too_short_experiments_are_rejected(self):
        from app.simulation.models import SimulationConfig
        from pydantic import ValidationError
        for config in ({'content_type':'unknown'}, {'content_type':'mechanisms'},
                       {'content_type':'design_comparison','idea_id':'destruction:0'},
                       {'content_type':'design_comparison','duration':20,'trial_count':6}):
            with self.subTest(config=config), self.assertRaises(ValidationError):
                SimulationConfig(**config)

    def test_comparison_preserves_challenge_and_changes_real_geometry(self):
        from app.simulation.models import SimulationConfig
        from app.simulation.director import SimulationDirector
        config = SimulationConfig(content_type='design_comparison',idea_id='design_comparison:0',duration=20,seed=42)
        scenario = SimulationDirector().generate(config)
        self.assertEqual(sum(segment.frame_count for segment in scenario.segments),600)
        self.assertEqual(len(scenario.experiments),3)
        self.assertTrue(all(trial.challenge==scenario.experiments[0].challenge for trial in scenario.experiments))
        self.assertEqual([trial.design.wheel_count for trial in scenario.experiments],[4,4,6])
        self.assertEqual(len({trial.design.wheel_track for trial in scenario.experiments}),3)
        self.assertEqual(scenario.results,[])  # No prewritten winner.

    def test_parameter_test_changes_only_declared_parameter(self):
        from app.simulation.models import SimulationConfig
        from app.simulation.director import SimulationDirector
        for index,parameter in enumerate(('wheel_radius','wheelbase','mass')):
            scenario = SimulationDirector().generate(SimulationConfig(content_type='parameter_test',
                idea_id=f'parameter_test:{index}',duration=20,seed=5))
            base = scenario.experiments[0].design.model_dump(exclude={'name',parameter})
            for trial in scenario.experiments:
                self.assertEqual(trial.controlled_variable,parameter)
                self.assertEqual(base,trial.design.model_dump(exclude={'name',parameter}))

    def test_retry_refinement_uses_outcome_and_does_not_promise_success(self):
        from app.simulation.models import SimulationConfig
        from app.simulation.director import SimulationDirector
        from app.simulation.experiments import refine_next_trial
        scenario = SimulationDirector().generate(SimulationConfig(content_type='improve_retry',duration=20,seed=42))
        previous,following = scenario.experiments[:2]
        refine_next_trial(previous,following,{'outcome':'failure'})
        self.assertLess(following.design.wheel_track,previous.design.wheel_track)
        self.assertLess(following.design.body_height,previous.design.body_height)
        self.assertEqual(following.challenge,previous.challenge)
        self.assertIsNotNone(following.refinement_reason)
        final = scenario.experiments[2]
        refine_next_trial(following,final,{'outcome':'success'})
        self.assertLess(final.design.mass,following.design.mass)

    def test_slices_stay_inside_one_trial_and_preserve_exact_duration(self):
        from app.simulation.models import SimulationConfig
        from app.simulation.director import SimulationDirector
        scenario = SimulationDirector().generate(SimulationConfig(content_type='destruction',duration=31,segment_seconds=2,seed=1))
        self.assertEqual(sum(s.frame_count for s in scenario.segments),31*30)
        self.assertTrue(all(s.frame_count<=60 for s in scenario.segments))
        for segment in scenario.segments:
            trial = next(t for t in scenario.experiments if t.id==segment.experiment_id)
            self.assertGreaterEqual(segment.start_frame,trial.start_frame)
            self.assertLessEqual(segment.start_frame+segment.frame_count,trial.start_frame+trial.frame_count)

    def test_limits_are_monotonic_and_survival_goal_matches_plan(self):
        from app.simulation.models import SimulationConfig
        from app.simulation.director import SimulationDirector
        scenario = SimulationDirector().generate(SimulationConfig(content_type='limit_test',duration=60,seed=1))
        spans = [trial.challenge['span'] for trial in scenario.experiments]
        self.assertEqual(spans,sorted(spans))
        self.assertGreater(spans[3],spans[2])
        survival = SimulationDirector().generate(SimulationConfig(content_type='survival',duration=20,seed=1))
        self.assertTrue(all(t.challenge['goal_x']==15 for t in survival.experiments))


class ContentApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_and_ideas_have_no_blender_dependency(self):
        import httpx
        from app.web.server import app
        from unittest.mock import patch
        with patch('app.simulation.blender_renderer.BlenderRenderer.check_available',side_effect=AssertionError('Do not start Blender')):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                catalog = await client.get('/api/simulation/catalog')
                self.assertEqual(catalog.status_code,200)
                self.assertEqual(len(catalog.json()['families']),17)
                response = await client.post('/api/simulation/ideas',json={'seed':42,'count':3})
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.json()['seed'],42)
                self.assertEqual(len(response.json()['ideas']),3)
                self.assertEqual((await client.post('/api/simulation/ideas',json={'content_type':'unknown'})).status_code,422)
                self.assertEqual((await client.post('/api/generate',json={'video_type':'physics_simulation_video','content_type':'mechanisms','duration':20})).status_code,422)

    async def test_new_request_round_trips_story_controls(self):
        from app.web.server import GenerateRequest
        request = GenerateRequest(video_type='physics_simulation_video',content_type='design_comparison',
                                  idea_id='design_comparison:0',duration=20,trial_count=3,show_labels=False)
        config = request.simulation_config()
        self.assertEqual(config.content_type,'design_comparison')
        self.assertEqual(config.idea_id,'design_comparison:0')
        self.assertFalse(config.show_labels)
