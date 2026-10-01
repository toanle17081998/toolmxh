from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class VisualMode(str, Enum):
    AUTO = "AUTO"
    STANDARD = "STANDARD"
    HEALTH_CHARACTER = "HEALTH_CHARACTER"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            return cls.__members__.get(value.upper())


Organ = Literal["heart", "liver", "kidney", "stomach", "lungs", "brain",
                "intestines", "pancreas", "bladder", "eye", "tooth"]
Environment = Literal["BLOODSTREAM_WORLD", "DIGESTIVE_WORLD", "RESPIRATORY_WORLD",
                      "NERVOUS_SYSTEM_WORLD", "ORGAN_ROOM", "MICROSCOPIC_WORLD"]


class HealthCharacter(BaseModel):
    organ: Organ
    shape: str
    color: str
    face_placement: str
    eyes: str = "two expressive dark brown eyes with ivory sclera, identical oval proportions"
    mouth: str = "small flexible expressive mouth, below the eyes"
    allowed_limbs: str = "two small flexible arms; no legs; limbs never obscure anatomy"
    proportions: str = "anatomy occupies at least 80 percent of the character silhouette"
    personality: str
    animation: str
    style: str = "polished high-quality 3D educational animation, cute but not childish, smooth materials, clear readable anatomy, soft cinematic lighting"
    negative_constraints: str = "no human in organ costume, no human protagonist, no superhero logo, no plush toy, no anatomical shape replaced by a generic person"
    seed: int
    reference_image: str | None = None

    def anchor(self) -> str:
        return (
            f"Recognizable anthropomorphic human {self.organ}: {self.shape}; {self.color}; "
            f"face placement: {self.face_placement}; {self.eyes}; {self.mouth}; "
            f"{self.allowed_limbs}; {self.proportions}; personality: {self.personality}; {self.style}."
        )


class HealthCharacterBible(BaseModel):
    version: int = 1
    characters: dict[str, HealthCharacter] = Field(default_factory=dict)


class MicroStory(BaseModel):
    setup: str = Field(min_length=5)
    action: str = Field(min_length=5)
    reaction: str = Field(min_length=5)


class HealthSemanticAnalysis(BaseModel):
    scene_id: int
    domain: Literal["health"] = "health"
    primary_subject: Organ
    secondary_subjects: list[Organ] = Field(default_factory=list)
    process: str = Field(min_length=2)
    condition_state: str
    cause: str | None = None
    effect: str | None = None
    visual_action: str = Field(min_length=5)
    character_emotion: str
    required_objects: list[str] = Field(default_factory=list)
    allowed_generic_visuals: list[str] = Field(default_factory=list)
    forbidden_generic_visuals: list[str] = Field(default_factory=lambda: [
        "doctor", "hospital", "nurse", "medical team", "person exercising",
        "person drinking water", "salad", "vegetables", "random medicine",
        "random laboratory", "generic anatomy chart", "stock footage",
    ])
    environment: Environment
    micro_story: MicroStory
    subject_movement: str = Field(min_length=5)
    environment_movement: str = Field(min_length=5)
    camera_movement: str = "slow clear medium-close cinematic push-in"
    biological_concept: str = Field(min_length=5)
    visual_metaphor: str | None = None
    uncertainty: str | None = None
    narration_qualifiers: str = "preserve the narration's certainty, timing and severity"


class HealthAnalysisBatch(BaseModel):
    scenes: list[HealthSemanticAnalysis]


class RelevanceScore(BaseModel):
    primary_subject_match: int = Field(ge=0, le=30)
    biological_process_match: int = Field(ge=0, le=30)
    cause_effect_match: int = Field(ge=0, le=20)
    action_match: int = Field(ge=0, le=10)
    visual_clarity: int = Field(ge=0, le=10)
    unrelated_generic_visuals: list[str] = Field(default_factory=list)
    contradicts_narration: bool = False
    explanation: str

    @property
    def total(self) -> int:
        return sum((self.primary_subject_match, self.biological_process_match,
                    self.cause_effect_match, self.action_match, self.visual_clarity))

    @property
    def accepted(self) -> bool:
        return self.total >= 80 and not self.unrelated_generic_visuals and not self.contradicts_narration


class HealthScenePlan(BaseModel):
    analysis: HealthSemanticAnalysis
    image_prompt: str
    video_prompt: str
    negative_prompt: str
    relevance: RelevanceScore
