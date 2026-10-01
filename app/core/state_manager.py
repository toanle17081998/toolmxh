import json
import os
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from app.models.project import ProjectConfig, ProjectState, PipelineStage, SceneStatus, SceneProgress
from app.config import settings

class ProjectStateManager:
    """Quản lý trạng thái vòng đời dự án, lưu trữ đĩa nguyên tử và hỗ trợ resume/retry."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = settings.PROJECTS_DIR / project_id
        self.state_file = self.project_dir / "project.json"

    def init_project_structure(self, config: ProjectConfig) -> ProjectState:
        """Khởi tạo toàn bộ cây thư mục chuẩn cho dự án video."""
        subdirs = [
            "research",
            "script",
            "storyboard",
            "characters",
            "audio",
            "scenes",
            "subtitles",
            "renders",
            "metadata",
            "logs"
        ]
        self.project_dir.mkdir(parents=True, exist_ok=True)
        for subdir in subdirs:
            (self.project_dir / subdir).mkdir(parents=True, exist_ok=True)

        if self.state_file.exists():
            return self.load_state()

        initial_state = ProjectState(
            config=config,
            stage=PipelineStage.CREATED,
            progress_percentage=0.0
        )
        self.save_state(initial_state)
        return initial_state

    def load_state(self) -> ProjectState:
        """Đọc trạng thái hiện tại từ file project.json."""
        if not self.state_file.exists():
            raise FileNotFoundError(f"Project state not found: {self.state_file}")
        with open(self.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ProjectState.model_validate(data)

    def save_state(self, state: ProjectState) -> None:
        """Ghi trạng thái nguyên tử (Atomic write qua file tạm) tránh hỏng dữ liệu khi crash."""
        temp_file = self.project_dir / "project.json.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))
        for attempt in range(6):
            try:
                temp_file.replace(self.state_file)
                return
            except PermissionError as error:
                # Windows readers/scanners can briefly deny atomic replacement.
                # Keep the original intact and retry only native sharing/access errors.
                if getattr(error,'winerror',None) not in (5,32,33) or attempt==5:
                    raise
                time.sleep(.02*2**attempt)

    def update_stage(self, stage: PipelineStage, progress: float) -> ProjectState:
        state = self.load_state()
        state.stage = stage
        state.progress_percentage = progress
        self.save_state(state)
        return state

    def init_scenes_progress(self, total_scenes: int) -> ProjectState:
        state = self.load_state()
        for i in range(1, total_scenes + 1):
            if i not in state.scenes_progress:
                scene_dir = self.get_scene_dir(i)
                scene_dir.mkdir(parents=True, exist_ok=True)
                state.scenes_progress[i] = SceneProgress(scene_id=i, status=SceneStatus.PENDING)
        self.save_state(state)
        return state

    def update_scene_status(
        self,
        scene_id: int,
        status: SceneStatus,
        image_path: Optional[str] = None,
        video_path: Optional[str] = None,
        duration: float = 0.0,
        error_message: Optional[str] = None
    ) -> ProjectState:
        state = self.load_state()
        if scene_id not in state.scenes_progress:
            state.scenes_progress[scene_id] = SceneProgress(scene_id=scene_id)
        
        sp = state.scenes_progress[scene_id]
        sp.status = status
        if image_path: sp.image_path = image_path
        if video_path: sp.video_path = video_path
        if duration > 0: sp.duration = duration
        if error_message: sp.error_message = error_message
        
        self.save_state(state)
        return state

    def get_scene_dir(self, scene_id: int) -> Path:
        scene_str = f"{scene_id:03d}"
        path = self.project_dir / "scenes" / scene_str
        path.mkdir(parents=True, exist_ok=True)
        return path

    def is_scene_completed(self, scene_id: int) -> bool:
        state = self.load_state()
        if scene_id not in state.scenes_progress:
            return False
        sp = state.scenes_progress[scene_id]
        if sp.status == SceneStatus.VIDEO_DONE and sp.video_path and Path(sp.video_path).exists():
            return True
        return False
