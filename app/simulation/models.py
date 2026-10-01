from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class SimulationConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    simulation_type: Literal['vehicle_obstacle'] = 'vehicle_obstacle'
    duration: int = Field(default=60, ge=1, le=1800)
    aspect_ratio: Literal['16:9', '9:16'] = '16:9'
    fps: Literal[24, 30] = 30
    quality: Literal['draft', 'standard', 'high'] = 'standard'
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)
    vehicle: Literal['brick_basic_car'] = 'brick_basic_car'
    color: Literal['random', 'red', 'blue', 'yellow', 'green', 'orange'] = 'random'
    theme: Literal['colorful_toy_world'] = 'colorful_toy_world'
    difficulty: int = Field(default=2, ge=1, le=3)
    music: bool = True
    sound_effects: bool = True
    engine_sound: bool = True
    segment_seconds: int = Field(default=30, ge=1, le=30)
    repetition_window: int = Field(default=8, ge=2, le=8)
    repetition_limit: int = Field(default=2, ge=2, le=4)

    def dimensions(self):
        width, height = {'draft': (480, 270), 'standard': (1280, 720), 'high': (1920, 1080)}[self.quality]
        return (height, width) if self.aspect_ratio == '9:16' else (width, height)


class TrackSection(BaseModel):
    type: str
    start: float
    length: float
    width: float = 5.0
    gap: float = 0
    difficulty: int = 1
    parameters: dict = Field(default_factory=dict)


class WorldState(BaseModel):
    vehicle_type: str = 'brick_basic_car'
    vehicle_color: str
    damage_state: list[str] = Field(default_factory=list)
    environment: str = 'colorful_toy_world'
    track_style: str = 'pastel_runway'
    lighting: str = 'studio'
    camera_style: str = 'dynamic_follow'
    difficulty: int = 1
    progress: float = 0
    position: tuple[float, float, float] = (0, 0, 0)
    pitch: float = 0
    wheel_angle: float = 0
    time: float = 0


class SegmentPlan(BaseModel):
    index: int
    seed: int
    start_frame: int
    frame_count: int
    start_state: WorldState
    end_state: WorldState
    sections: list[TrackSection]
    checkpoints: list[dict]


class Scenario(BaseModel):
    schema_version: int = 1
    mode: Literal['simulation_video'] = 'simulation_video'
    theme: str
    duration: int
    aspect_ratio: str
    fps: int
    seed: int
    quality: str
    vehicle: dict
    environment: dict
    camera: dict
    audio: dict
    speed: float = 3.0
    sections: list[TrackSection]
    events: list[dict]
    segments: list[SegmentPlan]


class SegmentProgress(BaseModel):
    segment_id: int
    status: Literal['PENDING', 'RENDERING', 'COMPLETED', 'FAILED'] = 'PENDING'
    attempts: int = 0
    seed: int
    duration: float
    output_path: str | None = None
    error: str | None = None
    checkpoint: dict = Field(default_factory=dict)
