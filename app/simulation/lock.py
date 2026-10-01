"""OS-backed ownership shared by CLI/web workers; automatically released on exit."""
import os
from pathlib import Path


class ProjectBusy(RuntimeError):
    pass


class ProjectLease:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.handle = None

    def __enter__(self):
        self.directory.mkdir(parents=True,exist_ok=True)
        self.handle = (self.directory/'.simulation.lock').open('a+b')
        if self.handle.seek(0,os.SEEK_END)==0:
            self.handle.write(b'\0')
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error:
            self.handle.close()
            self.handle = None
            raise ProjectBusy(f'Project already running in another process: {self.directory.name}') from error
        return self

    def __exit__(self,*args):
        if self.handle is not None:
            try:
                self.handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(self.handle.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
            finally:
                self.handle.close()
                self.handle = None


def project_is_running(directory):
    directory = Path(directory)
    if not directory.is_dir():
        return False
    try:
        with ProjectLease(directory):
            return False
    except ProjectBusy:
        return True
