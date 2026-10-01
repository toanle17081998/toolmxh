import tempfile
import unittest
from pathlib import Path


class ProjectOwnershipTest(unittest.TestCase):
    def test_second_owner_is_rejected_and_closed_owner_can_be_reacquired(self):
        from app.simulation.lock import ProjectLease, ProjectBusy, project_is_running
        with tempfile.TemporaryDirectory() as directory:
            first = ProjectLease(Path(directory))
            with first:
                self.assertTrue(project_is_running(Path(directory)))
                with self.assertRaises(ProjectBusy):
                    with ProjectLease(Path(directory)):
                        self.fail('Duplicate render ownership acquired')
            self.assertFalse(project_is_running(Path(directory)))
            with ProjectLease(Path(directory)):
                self.assertTrue(project_is_running(Path(directory)))

    def test_subprocess_exit_releases_ownership(self):
        import subprocess
        import sys
        from app.simulation.lock import ProjectLease, project_is_running
        with tempfile.TemporaryDirectory() as directory:
            script = "import sys; from pathlib import Path; from app.simulation.lock import ProjectLease; lease=ProjectLease(Path(sys.argv[1])); lease.__enter__(); print('locked',flush=True); sys.stdin.readline()"
            process = subprocess.Popen([sys.executable,'-c',script,directory],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
            try:
                self.assertEqual(process.stdout.readline().strip(),'locked')
                self.assertTrue(project_is_running(Path(directory)))
            finally:
                process.kill()
                process.wait(timeout=10)
                process.stdin.close()
                process.stdout.close()
            self.assertFalse(project_is_running(Path(directory)))

