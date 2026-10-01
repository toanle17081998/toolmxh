from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class PipelineStage(str, Enum):
    CREATED = "CREATED"
    RESEARCH = "RESEARCH"
    SCRIPT = "SCRIPT"
    STORYBOARD = "STORYBOARD"
    CHARACTER_GENERATION = "CHARACTER_GENERATION"
    VOICE_GENERATION = "VOICE_GENERATION"
    TIMELINE = "TIMELINE"
    VISUAL_GENERATION = "VISUAL_GENERATION"
    AUDIO_MIXING = "AUDIO_MIXING"
    SUBTITLE = "SUBTITLE"
    COMPOSITING = "COMPOSITING"
    QC = "QC"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class SceneStatus(str, Enum):
    PENDING = "PENDING"
    GENERATING_IMAGE = "GENERATING_IMAGE"
    IMAGE_DONE = "IMAGE_DONE"
    GENERATING_VIDEO = "GENERATING_VIDEO"
    VIDEO_DONE = "VIDEO_DONE"
    FAILED = "FAILED"

class SceneProgress(BaseModel):
    scene_id: int
    status: SceneStatus = SceneStatus.PENDING
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    duration: float = 0.0
    error_message: Optional[str] = None

class ProjectConfig(BaseModel):
    project_id: str
    topic: str
    platform: str = "tiktok"  # tiktok, shorts, reels, youtube
    target_duration: int = 60
    language: str = "vi"
    style: str = "Cinematic Documentary"
    voice: str = "vi-VN-HoaiMyNeural"
    video_model: str = "AUTO"  # AUTO, WAN, LTX, HUNYUAN, COMFYUI, FAL
    created_at: datetime = Field(default_factory=datetime.now)

class ProjectState(BaseModel):
    config: ProjectConfig
    stage: PipelineStage = PipelineStage.CREATED
    progress_percentage: float = 0.0
    scenes_progress: Dict[int, SceneProgress] = {}
    master_video_path: Optional[str] = None
    tiktok_video_path: Optional[str] = None
    youtube_video_path: Optional[str] = None
    narration_audio_path: Optional[str] = None
    subtitle_ass_path: Optional[str] = None
    subtitle_srt_path: Optional[str] = None
    metadata_path: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    errors: List[str] = []
