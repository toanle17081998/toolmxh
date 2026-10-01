import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class AtomicStateWriteTest(unittest.TestCase):
    def test_temporary_windows_share_denial_retries_without_truncating_original(self):
        from app.config import settings
        from app.core.state_manager import ProjectStateManager
        from app.models.project import ProjectConfig
        with tempfile.TemporaryDirectory() as root, patch.object(settings,'PROJECTS_DIR',Path(root)):
            manager = ProjectStateManager('atomic_retry')
            state = manager.init_project_structure(ProjectConfig(project_id='atomic_retry',topic='test'))
            original = manager.state_file.read_text(encoding='utf-8')
            state.progress_percentage = 50
            calls = []
            replace = Path.replace
            def blocked_once(source,destination):
                calls.append(str(source))
                if len(calls)==1:
                    self.assertEqual(manager.state_file.read_text(encoding='utf-8'),original)
                    error = PermissionError('sharing violation')
                    error.winerror = 32
                    raise error
                return replace(source,destination)
            with patch.object(Path,'replace',blocked_once), patch('app.core.state_manager.time.sleep') as sleep:
                manager.save_state(state)
            self.assertEqual(len(calls),2)
            sleep.assert_called_once_with(.02)
            self.assertEqual(manager.load_state().progress_percentage,50)

    def test_permanent_windows_denial_is_bounded_and_preserves_previous_state(self):
        from app.config import settings
        from app.core.state_manager import ProjectStateManager
        from app.models.project import ProjectConfig
        with tempfile.TemporaryDirectory() as root, patch.object(settings,'PROJECTS_DIR',Path(root)):
            manager = ProjectStateManager('atomic_denied')
            state = manager.init_project_structure(ProjectConfig(project_id='atomic_denied',topic='test'))
            original = manager.state_file.read_text(encoding='utf-8')
            error = PermissionError('access denied')
            error.winerror = 5
            with patch.object(Path,'replace',side_effect=error) as replace, patch('app.core.state_manager.time.sleep'):
                with self.assertRaises(PermissionError):
                    manager.save_state(state)
            self.assertEqual(replace.call_count,6)
            self.assertEqual(manager.state_file.read_text(encoding='utf-8'),original)
