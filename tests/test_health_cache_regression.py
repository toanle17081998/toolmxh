import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch

from app.health.generation import HealthVisualGenerator
from app.health.models import HealthScenePlan, VisualMode
from app.health.planner import HealthVisualPlanner, build_health_prompts, save_json
from app.health.quality import quality_script
from app.health.registry import HealthCharacterRegistry, resolve_visual_mode
from test_health_visuals import quality_analyses, score


class HealthCacheRegressionTest(unittest.IsolatedAsyncioTestCase):
    def test_technology_metaphors_do_not_force_anatomy_mode(self):
        for text in ('The brain of an AI system','Eye tracking technology','Computer memory and sleep',
                     'Bộ não của máy tính','Mắt camera và thuật toán'):
            with self.subTest(text=text):
                self.assertEqual(resolve_visual_mode(text),VisualMode.STANDARD)
        self.assertEqual(resolve_visual_mode('AI detects human retina disease'),VisualMode.HEALTH_CHARACTER)
        self.assertEqual(resolve_visual_mode('How sleep helps brain health'),VisualMode.HEALTH_CHARACTER)

    async def test_accepted_plan_cache_preserves_unmodified_actual_review(self):
        script = quality_script('kidney')
        batch = {'scenes':[item.model_dump() for item in quality_analyses('kidney')]}
        llm = MagicMock(complete_json=AsyncMock(side_effect=[batch,*[score().model_dump() for _ in script.scenes]]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            await HealthVisualPlanner(llm).plan(script,root)
            debug_path = root/'health_debug'/'scene_001.json'
            debug = json.loads(debug_path.read_text(encoding='utf-8'))
            debug['actual_visual_review'] = {'explanation':'Artifact-specific review must survive cache reuse'}
            save_json(debug_path,debug)
            before = debug_path.read_bytes()
            unused = MagicMock(complete_json=AsyncMock(side_effect=AssertionError('Accepted plans should not call LLM')))
            await HealthVisualPlanner(unused).plan(script,root)
            unused.complete_json.assert_not_awaited()
            self.assertEqual(debug_path.read_bytes(),before)
            partial = MagicMock(complete_json=AsyncMock(side_effect=[batch,score().model_dump()]))
            await HealthVisualPlanner(partial).plan(script,root,invalidated_scene_ids=[2])
            self.assertEqual(partial.complete_json.await_count,2)  # One analysis + only the invalidated review.
            self.assertEqual(debug_path.read_bytes(),before)

    def test_visual_fingerprint_ignores_review_prose_but_tracks_timeline_and_size(self):
        item = quality_analyses('kidney')[0]
        bible = HealthCharacterRegistry.bible(['kidney'])
        image,video,negative = build_health_prompts(item,bible)
        plan = HealthScenePlan(analysis=item,image_prompt=image,video_prompt=video,negative_prompt=negative,relevance=score())
        with tempfile.TemporaryDirectory() as directory:
            reference = Path(directory)/'reference.png'
            reference.write_bytes(b'fixed reference evidence')
            bible.characters['kidney'].reference_image = str(reference)
            baseline = HealthVisualGenerator.fingerprint('Kidneys filter blood',plan,bible,duration=3,width=720,height=1280)
            plan.relevance.explanation = 'Different review wording for the same accepted content'
            self.assertEqual(baseline,HealthVisualGenerator.fingerprint('Kidneys filter blood',plan,bible,duration=3,width=720,height=1280))
            self.assertNotEqual(baseline,HealthVisualGenerator.fingerprint('Kidneys filter blood',plan,bible,duration=4,width=720,height=1280))
            self.assertNotEqual(baseline,HealthVisualGenerator.fingerprint('Kidneys filter blood',plan,bible,duration=3,width=1280,height=720))

    async def test_factory_regeneration_reuses_saved_script_without_research_or_script_llm(self):
        from app.config import settings
        from app.core.state_manager import ProjectStateManager
        from app.models.project import ProjectConfig
        from app.factory import VietnameseVideoFactory
        from app.providers.llm.offline import OfflineBrainProvider
        script = quality_script('kidney')
        storyboard = await OfflineBrainProvider().generate_storyboard(script)
        llm = MagicMock(research_topic=AsyncMock(side_effect=AssertionError('Do not repeat research')),
                        generate_script=AsyncMock(side_effect=AssertionError('Do not replace saved narration')),
                        generate_storyboard=AsyncMock(return_value=storyboard))
        with tempfile.TemporaryDirectory() as directory, patch.object(settings,'PROJECTS_DIR',Path(directory)), \
                patch('app.factory.get_llm_provider',return_value=llm), \
                patch('app.factory.get_image_provider',return_value=MagicMock()), \
                patch('app.factory.get_video_provider',return_value=MagicMock()), \
                patch('app.factory.get_tts_provider',return_value=MagicMock()):
            manager = ProjectStateManager('saved_script')
            manager.init_project_structure(ProjectConfig(project_id='saved_script',topic='Kidney filtration'))
            path = manager.project_dir/'script'/'script.json'
            path.write_text(script.model_dump_json(indent=2),encoding='utf-8')
            before = path.read_bytes()
            factory = VietnameseVideoFactory(console_output=False,visual_mode='STANDARD')
            factory.timeline_engine.build_timeline = AsyncMock(side_effect=RuntimeError('stop after planning'))
            with self.assertRaisesRegex(RuntimeError,'stop after planning'):
                await factory.generate_video('Kidney filtration',project_id='saved_script')
            llm.research_topic.assert_not_awaited()
            llm.generate_script.assert_not_awaited()
            self.assertEqual(path.read_bytes(),before)
