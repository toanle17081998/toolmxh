from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SimulationConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    simulation_type: Literal['brick_physics_experiment','brick_vehicle_obstacle', 'vehicle_obstacle'] = 'brick_vehicle_obstacle'
    duration: int = Field(default=60, ge=1, le=1800)
    aspect_ratio: Literal['16:9', '9:16'] = '16:9'
    fps: Literal[24, 30] = 30
    quality: Literal['preview', 'draft', 'standard', 'high'] = 'preview'
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)
    vehicle: Literal['brick_crawler', 'brick_basic_car'] = 'brick_crawler'
    color: Literal['random', 'red', 'blue', 'yellow', 'green', 'orange'] = 'red'
    theme: Literal['minimal_gray_track', 'colorful_toy_world'] = 'minimal_gray_track'
    difficulty: int = Field(default=2, ge=1, le=3)
    music: bool = False
    sound_effects: bool = True
    engine_sound: bool = True
    sound: Literal['sfx_only', 'sfx_and_music', 'music_only', 'silent'] | None = None
    camera_style: Literal['dynamic_follow', 'follow', 'side_follow', 'low_follow', 'front_obstacle', 'top_down', 'static'] = 'dynamic_follow'
    segment_seconds: int = Field(default=30, ge=1, le=30)
    repetition_window: Literal[8] = 8
    repetition_limit: Literal[2] = 2
    content_type: str = 'obstacle_course'
    idea_id: str | None = None
    trial_count: int = Field(default=3, ge=1, le=8)
    show_labels: bool = True

    @field_validator('content_type', mode='before')
    @classmethod
    def validate_content(cls, value):
        from app.simulation.content import validate_content_type
        return validate_content_type(value.lower() if isinstance(value, str) else value)

    @model_validator(mode='after')
    def validate_idea(self):
        if self.idea_id:
            from app.simulation.content import SimulationIdeaGenerator, validate_content_type
            idea = SimulationIdeaGenerator().resolve(self.idea_id, self.seed or 0)
            validate_content_type(idea['content_type'])
            if self.content_type not in ('auto', idea['content_type']):
                raise ValueError('Idea does not belong to the selected content type')
        if self.content_type != 'obstacle_course' and self.duration < self.trial_count*4:
            raise ValueError('Each trial needs at least four seconds; reduce trials or increase duration')
        return self

    @field_validator('vehicle','theme',mode='before')
    @classmethod
    def normalize_legacy_assets(cls,value):
        return {'brick_basic_car':'brick_crawler','colorful_toy_world':'minimal_gray_track'}.get(value,value)

    @field_validator('difficulty', mode='before')
    @classmethod
    def normalize_difficulty(cls, value):
        return {'easy':1,'progressive':2,'hard':3}.get(value.lower(),value) if isinstance(value,str) else value

    @field_validator('quality','sound','camera_style','simulation_type',mode='before')
    @classmethod
    def normalize_choice(cls,value):
        return value.lower() if isinstance(value,str) else value

    def dimensions(self):
        width, height = {'preview': (480, 270), 'draft': (480, 270), 'standard': (1280, 720), 'high': (1920, 1080)}[self.quality]
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
    rotation: tuple[float,float,float,float] = (1,0,0,0)
    physical_bodies: list[dict] = Field(default_factory=list)


class SegmentPlan(BaseModel):
    index: int
    seed: int
    start_frame: int
    frame_count: int
    start_state: WorldState
    end_state: WorldState
    sections: list[TrackSection]
    checkpoints: list[dict]
    experiment_id: int | None = None


class VehicleDesign(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = 'Crawler'
    body_width: float = Field(default=1.12, ge=.6, le=1.8)
    wheel_track: float = Field(default=1.58, ge=1.1, le=2.5)
    wheelbase: float = Field(default=1.56, ge=1, le=2.8)
    wheel_radius: float = Field(default=.46, ge=.3, le=.7)
    wheel_count: Literal[4, 6] = 4
    body_height: float = Field(default=1, ge=.6, le=1.4)
    mass: float = Field(default=2.8, ge=1, le=9)
    bumper_length: float = Field(default=.16, ge=.12, le=.5)
    payload_mass: float = Field(default=0, ge=0, le=6)
    payload_height: float = Field(default=1.15, ge=1.05, le=2)

    @model_validator(mode='after')
    def wheel_clearance(self):
        if self.wheel_track < self.body_width + .34:
            raise ValueError('Wheels overlap the chassis; increase wheel track')
        return self


class ExperimentPlan(BaseModel):
    id: int
    start_frame: int
    frame_count: int
    assembly_frames: int = 0
    kind: str
    label: str
    design: VehicleDesign = Field(default_factory=VehicleDesign)
    challenge: dict = Field(default_factory=dict)
    controlled_variable: str = 'design'
    refinement_reason: str | None = None


class Scenario(BaseModel):
    schema_version: int = 1
    mode: Literal['physics_simulation_video', 'simulation_video'] = 'physics_simulation_video'
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
    physics: bool = True
    content_type: str = 'obstacle_course'
    idea: dict = Field(default_factory=dict)
    experiments: list[ExperimentPlan] = Field(default_factory=list)
    results: list[dict] = Field(default_factory=list)
    show_labels: bool = False


class SegmentProgress(BaseModel):
    segment_id: int
    status: Literal['PENDING', 'RENDERING', 'COMPLETED', 'FAILED'] = 'PENDING'
    attempts: int = 0
    seed: int
    duration: float
    output_path: str | None = None
    error: str | None = None
    checkpoint: dict = Field(default_factory=dict)
