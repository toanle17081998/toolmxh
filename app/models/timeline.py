from typing import List, Optional
from pydantic import BaseModel, Field

class WordTimestamp(BaseModel):
    word: str
    start_time: float  # seconds
    end_time: float    # seconds

class SceneTiming(BaseModel):
    scene_id: int
    start_time: float
    end_time: float
    duration: float
    narration_audio_path: str
    words: List[WordTimestamp] = []

class AudioTimeline(BaseModel):
    total_duration: float
    scenes: List[SceneTiming]
    master_narration_path: str
    bgm_path: Optional[str] = None
