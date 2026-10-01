import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator, model_validator

from app.config import settings
from app.factory import VietnameseVideoFactory
from app.core.state_manager import ProjectStateManager
from app.core.topic_suggester import TopicExplorerService
from app.models.project import ProjectConfig, PipelineStage, SceneStatus, VideoType
from app.simulation.models import SimulationConfig
from app.simulation.service import SimulationVideoService, prepare_simulation_project
from app.simulation.lock import ProjectBusy, ProjectLease, project_is_running

app = FastAPI(title="Vietnamese Generative Video Factory UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thư mục template
WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

class GenerateRequest(BaseModel):
    topic: str = ''
    video_type: VideoType = VideoType.SHORT_CONTENT
    duration: int = 60
    platform: str = "tiktok"
    style: str = "Cinematic Documentary"
    llm_model: str = "gemini-3.8-flash"
    image_model: str = "auto"
    video_model: str = "wan2.1"
    voice: str = "namminh"
    mascot: Optional[str] = "dr_bear"
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None
    simulation_type: str = 'vehicle_obstacle'
    aspect_ratio: Optional[str] = None
    quality: str = 'standard'
    seed: Optional[int] = None
    vehicle: str = 'brick_basic_car'
    color: str = 'random'
    theme: str = 'colorful_toy_world'
    difficulty: int = 2
    music: bool = True
    sound_effects: bool = True
    engine_sound: bool = True

    @field_validator('video_type', mode='before')
    @classmethod
    def normalize_mode(cls, value):
        return value.lower() if isinstance(value,str) else value

    def simulation_config(self):
        aspect = self.aspect_ratio or ('9:16' if 'platform' in self.model_fields_set and self.platform in ('tiktok','shorts','reels') else '16:9')
        return SimulationConfig(simulation_type=self.simulation_type,duration=self.duration,aspect_ratio=aspect,
                                quality=self.quality,seed=self.seed,vehicle=self.vehicle,color=self.color,
                                theme=self.theme,difficulty=self.difficulty,music=self.music,
                                sound_effects=self.sound_effects,engine_sound=self.engine_sound)

    @model_validator(mode='after')
    def validate_mode(self):
        if self.video_type == VideoType.SIMULATION_VIDEO:
            self.simulation_config()
            if not 30 <= self.duration <= 180:
                raise ValueError('Simulation MVP supports 30–180 seconds; longer durations are not yet enabled')
        elif not self.topic.strip():
            raise ValueError('Short Content requires a topic')
        return self

class SettingsUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    fal_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    openai_api_key: Optional[str] = None
    pexels_api_key: Optional[str] = None
    comfyui_server_url: Optional[str] = None

# Task background runner
active_projects: Dict[str, Any] = {}
running_projects: set[str] = set()

async def run_factory_task(project_id: str, req: GenerateRequest):
    try:
        if req.video_type == VideoType.SIMULATION_VIDEO:
            res = await SimulationVideoService().generate_video(project_id,req.simulation_config())
            active_projects[project_id] = {'status':'COMPLETED','result':res}
            return
        factory = VietnameseVideoFactory(
            console_output=False,
            voice=req.voice,
            gemini_key=req.gemini_key,
            openai_key=req.openai_key,
            llm_model=req.llm_model,
            image_model=req.image_model,
            video_model=req.video_model,
            mascot=req.mascot or "auto"
        )
        res = await factory.generate_video(
            topic=req.topic,
            duration=req.duration,
            platform=req.platform,
            language="vi",
            project_id=project_id
        )
        active_projects[project_id] = {"status": "COMPLETED", "result": res}
    except ProjectBusy as error:
        active_projects[project_id] = {'status':'RUNNING','message':str(error)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        active_projects[project_id] = {"status": "FAILED", "error": error_msg}
        if req.video_type == VideoType.SIMULATION_VIDEO:
            # The service persists failures while it still owns the project lease.
            return
        try:
            state_mgr = ProjectStateManager(project_id)
            if state_mgr.state_file.exists():
                state = state_mgr.load_state()
                state.stage = PipelineStage.FAILED
                state.errors.append(error_msg)
                state_mgr.save_state(state)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Could not persist failed project %s',project_id)
    finally:
        running_projects.discard(project_id)

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard template not found")
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/generate")
async def start_generation(req: GenerateRequest, background_tasks: BackgroundTasks):
    import uuid
    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    if req.video_type == VideoType.SIMULATION_VIDEO:
        prepare_simulation_project(project_id,req.simulation_config())
    active_projects[project_id] = {"status": "RUNNING"}
    running_projects.add(project_id)
    background_tasks.add_task(run_factory_task, project_id, req)
    return {"project_id": project_id, "status": "STARTED"}

@app.get("/api/progress/{project_id}")
async def get_progress(project_id: str):
    state_mgr = ProjectStateManager(project_id)
    if not state_mgr.state_file.exists():
        return {"project_id": project_id, "stage": "PENDING", "progress_percentage": 0.0}
    try:
        state = state_mgr.load_state()
        data = state.model_dump()
        data['is_running'] = project_id in running_projects or (state.config.video_type == VideoType.SIMULATION_VIDEO and project_is_running(state_mgr.project_dir))
        # Thêm thông tin kết quả nếu đã hoàn thành
        if project_id in active_projects:
            data["task_info"] = active_projects[project_id]
        return data
    except Exception as e:
        return {"project_id": project_id, "error": str(e)}

@app.post("/api/regenerate/{project_id}/{scene_id}")
async def regenerate_scene(project_id: str, scene_id: int, background_tasks: BackgroundTasks):
    state_mgr = ProjectStateManager(project_id)
    if not state_mgr.state_file.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    state = state_mgr.load_state()
    if state.config.video_type == VideoType.SIMULATION_VIDEO:
        if project_id in running_projects:
            raise HTTPException(status_code=409,detail='Project already running')
        try:
            with ProjectLease(state_mgr.project_dir):
                state = state_mgr.load_state()
                if scene_id not in state.segments_progress:
                    raise HTTPException(status_code=404,detail='Segment not found')
                state.segments_progress[scene_id].status = 'PENDING'
                state_mgr.save_state(state)
        except ProjectBusy as error:
            raise HTTPException(status_code=409,detail=str(error)) from error
        return await resume_simulation(project_id,background_tasks)
    
    state_mgr.update_scene_status(scene_id, SceneStatus.PENDING)
    state = state_mgr.load_state()

    req = GenerateRequest(
        topic=state.config.topic,
        duration=state.config.target_duration,
        platform=state.config.platform,
        style=state.config.style,
        llm_model=getattr(state.config, "llm_model", "gemini-3.8-flash"),
        image_model=getattr(state.config, "image_model", "gemini-3-pro-image-preview"),
        video_model=getattr(state.config, "video_model", "cinematic"),
        voice=getattr(state.config, "voice", "onyx")
    )
    background_tasks.add_task(run_factory_task, project_id, req)
    return {"project_id": project_id, "scene_id": scene_id, "status": "REGENERATING"}

@app.post('/api/resume/{project_id}')
async def resume_simulation(project_id: str, background_tasks: BackgroundTasks):
    manager = ProjectStateManager(project_id)
    if not manager.state_file.exists():
        raise HTTPException(status_code=404,detail='Project not found')
    state = manager.load_state()
    if state.config.video_type != VideoType.SIMULATION_VIDEO or state.config.simulation is None:
        raise HTTPException(status_code=400,detail='Resume endpoint is for simulation projects')
    if project_id in running_projects or project_is_running(manager.project_dir):
        raise HTTPException(status_code=409,detail='Project already running')
    req = GenerateRequest(video_type='simulation_video', **{k:v for k,v in state.config.simulation.model_dump().items()
                          if k in GenerateRequest.model_fields})
    running_projects.add(project_id)
    active_projects[project_id] = {'status':'RUNNING'}
    background_tasks.add_task(run_factory_task,project_id,req)
    return {'project_id':project_id,'status':'RESUMING'}

@app.get("/api/projects")
async def list_projects():
    projects_dir = settings.PROJECTS_DIR
    if not projects_dir.exists():
        return []
    result = []
    for p in sorted(projects_dir.iterdir(), key=os.path.getmtime, reverse=True):
        if p.is_dir() and (p / "project.json").exists():
            try:
                state = ProjectStateManager(p.name).load_state()
                result.append({
                    "project_id": p.name,
                    "topic": state.config.topic,
                    "platform": state.config.platform,
                    "video_type": state.config.video_type,
                    "stage": state.stage,
                    "created_at": state.config.created_at.strftime("%Y-%m-%d %H:%M")
                })
            except Exception:
                continue
    return result

@app.get("/api/topics/suggest")
async def get_topic_suggestions(
    keyword: Optional[str] = None,
    category: Optional[str] = "all",
    brain: str = "auto",
    use_ai: bool = False
):
    if use_ai:
        topics = await TopicExplorerService.generate_ai_suggestions(
            keyword=keyword,
            category=category,
            brain=brain
        )
    else:
        topics = TopicExplorerService.get_curated_topics(
            keyword=keyword,
            category=category
        )
    return {"topics": topics, "category": category, "count": len(topics)}

@app.get("/api/topics/random-live")
async def get_random_live_topic(category: Optional[str] = "all"):
    """Tạo trực tiếp 1 chủ đề viral mới toanh qua Live AI realtime."""
    topic = await TopicExplorerService.generate_single_live_trend(category=category)
    return {"topic": topic}

@app.get("/api/settings")
async def get_system_settings():
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    fal_key = os.getenv("FAL_KEY") or settings.FAL_KEY
    replicate_token = os.getenv("REPLICATE_API_TOKEN") or settings.REPLICATE_API_TOKEN
    return {
        "has_gemini_key": bool(gemini_key),
        "gemini_key_preview": f"{gemini_key[:6]}...{gemini_key[-4:]}" if gemini_key and len(gemini_key) > 10 else None,
        "has_openai_key": bool(openai_key),
        "openai_key_preview": f"{openai_key[:6]}...{openai_key[-4:]}" if openai_key and len(openai_key) > 10 else None,
        "has_fal_key": bool(fal_key),
        "fal_key_preview": f"{fal_key[:6]}...{fal_key[-4:]}" if fal_key and len(fal_key) > 10 else None,
        "has_replicate_token": bool(replicate_token),
        "replicate_token_preview": f"{replicate_token[:6]}...{replicate_token[-4:]}" if replicate_token and len(replicate_token) > 10 else None,
        "comfyui_server_url": settings.COMFYUI_SERVER_URL
    }

@app.post("/api/settings")
async def update_system_settings(req: SettingsUpdateRequest):
    env_file = settings.WORKSPACE_DIR / ".env"
    env_lines = []
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            env_lines = f.readlines()

    keys_map = {}
    for line in env_lines:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            keys_map[k] = v

    if req.gemini_api_key:
        keys_map["GEMINI_API_KEY"] = req.gemini_api_key
        os.environ["GEMINI_API_KEY"] = req.gemini_api_key
        settings.GEMINI_API_KEY = req.gemini_api_key
    if req.fal_api_key:
        keys_map["FAL_KEY"] = req.fal_api_key
        os.environ["FAL_KEY"] = req.fal_api_key
        settings.FAL_KEY = req.fal_api_key
    if req.replicate_api_token:
        keys_map["REPLICATE_API_TOKEN"] = req.replicate_api_token
        os.environ["REPLICATE_API_TOKEN"] = req.replicate_api_token
        settings.REPLICATE_API_TOKEN = req.replicate_api_token
    if req.openai_api_key:
        keys_map["OPENAI_API_KEY"] = req.openai_api_key
        os.environ["OPENAI_API_KEY"] = req.openai_api_key
        settings.OPENAI_API_KEY = req.openai_api_key
    if req.pexels_api_key:
        keys_map["PEXELS_API_KEY"] = req.pexels_api_key
        os.environ["PEXELS_API_KEY"] = req.pexels_api_key
        settings.PEXELS_API_KEY = req.pexels_api_key
    if req.comfyui_server_url:
        keys_map["COMFYUI_SERVER_URL"] = req.comfyui_server_url
        settings.COMFYUI_SERVER_URL = req.comfyui_server_url

    with open(env_file, "w", encoding="utf-8") as f:
        for k, v in keys_map.items():
            f.write(f"{k}={v}\n")

    return {"status": "SUCCESS", "message": "Đã lưu cài đặt API Keys thành công!"}

# Endpoint phát video trực tiếp cho browser
@app.get("/media/{project_id}/video")
async def get_project_video(project_id: str):
    vid = settings.OUTPUTS_DIR / project_id / "final.mp4"
    if not vid.exists():
        vid = settings.PROJECTS_DIR / project_id / "renders" / "master.mp4"
    if not vid.exists():
        vid = settings.PROJECTS_DIR / project_id / "final" / "video.mp4"
    if not vid.exists():
        vid = settings.PROJECTS_DIR / project_id / "final.mp4"
    if not vid.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(str(vid), media_type="video/mp4")

# Endpoint tải file artifact
@app.get("/media/{project_id}/artifact/{filename}")
async def get_artifact(project_id: str, filename: str):
    allowed = ["final.mp4", "thumbnail.png", "script.txt", "subtitle.srt", "metadata.json", "scenario.json"]
    if filename not in allowed:
        raise HTTPException(status_code=403, detail="File không được phép truy cập")
    p = settings.OUTPUTS_DIR / project_id / filename
    if not p.exists():
        p = settings.PROJECTS_DIR / project_id / filename
    if not p.exists() and filename == "metadata.json":
        p = settings.PROJECTS_DIR / project_id / "metadata" / "metadata.json"
    if not p.exists() and filename == "metadata.json":
        p = settings.PROJECTS_DIR / project_id / "project.json"
    if not p.exists() and filename == "final.mp4":
        p = settings.PROJECTS_DIR / project_id / "final" / "video.mp4"
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(p), filename=filename)
