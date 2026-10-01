from typing import List, Optional
from pydantic import BaseModel, Field

class CharacterBible(BaseModel):
    character_id: str
    name: str
    gender: str = "male"
    age: int = 35
    appearance: str
    hair: str = "short black hair"
    clothing: str = "futuristic explorer jacket"
    reference_image: Optional[str] = None
    seed: int = 12345

class VisualStyleBible(BaseModel):
    style: str = "cinematic documentary"
    lighting: str = "dramatic volumetric lighting, rim light"
    lens: str = "35mm anamorphic cinema lens"
    contrast: str = "rich shadows with high contrast"
    camera: str = "Arri Alexa Mini LF 8k"
    render_style: str = "photorealistic, hyper-detailed, masterpiece"

class SceneStoryboard(BaseModel):
    scene_id: int
    duration: float = 5.0
    narration: str
    subject: str
    environment: str
    lighting: str
    camera_angle: str
    camera_movement: str
    visual_style: str
    video_prompt: str
    image_prompt: str
    negative_prompt: str = "ugly, distorted, blurry, bad anatomy, text, watermark, logo, low quality, artifacts"
    transition: str = "cut"
    sound_effect: Optional[str] = None
    continuity_reference: Optional[str] = None

class Storyboard(BaseModel):
    project_id: str
    visual_bible: VisualStyleBible = Field(default_factory=VisualStyleBible)
    characters: List[CharacterBible] = []
    scenes: List[SceneStoryboard]
