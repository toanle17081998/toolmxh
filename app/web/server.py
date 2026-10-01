import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.factory import VietnameseVideoFactory
from app.core.state_manager import ProjectStateManager
from app.models.project import ProjectConfig, PipelineStage, SceneStatus

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
    topic: str
    duration: int = 60
    platform: str = "tiktok"
    style: str = "Cinematic Documentary"
    llm_model: str = "gemini-3.8-flash"
    image_model: str = "real_media"
    video_model: str = "cinematic"
    voice: str = "charon"
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None

class SettingsUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    fal_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    comfyui_server_url: Optional[str] = None

# Task background runner
active_projects: Dict[str, Any] = {}

async def run_factory_task(project_id: str, req: GenerateRequest):
    try:
        factory = VietnameseVideoFactory(
            console_output=True,
            voice=req.voice,
            gemini_key=req.gemini_key,
            openai_key=req.openai_key,
            llm_model=req.llm_model,
            image_model=req.image_model,
            video_model=req.video_model
        )
        res = await factory.generate_video(
            topic=req.topic,
            duration=req.duration,
            platform=req.platform,
            language="vi",
            project_id=project_id
        )
        active_projects[project_id] = {"status": "COMPLETED", "result": res}
    except Exception as e:
        active_projects[project_id] = {"status": "FAILED", "error": str(e)}

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
    active_projects[project_id] = {"status": "RUNNING"}
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
                    "stage": state.stage,
                    "created_at": state.config.created_at.strftime("%Y-%m-%d %H:%M")
                })
            except Exception:
                continue
    return result

@app.get("/api/settings")
async def get_system_settings():
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    return {
        "has_gemini_key": bool(gemini_key),
        "gemini_key_preview": f"{gemini_key[:6]}...{gemini_key[-4:]}" if gemini_key and len(gemini_key) > 10 else None,
        "has_openai_key": bool(openai_key),
        "openai_key_preview": f"{openai_key[:6]}...{openai_key[-4:]}" if openai_key and len(openai_key) > 10 else None,
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
    if req.openai_api_key:
        keys_map["OPENAI_API_KEY"] = req.openai_api_key
        os.environ["OPENAI_API_KEY"] = req.openai_api_key
        settings.OPENAI_API_KEY = req.openai_api_key
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
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(str(vid), media_type="video/mp4")

# Endpoint tải file artifact
@app.get("/media/{project_id}/artifact/{filename}")
async def get_artifact(project_id: str, filename: str):
    allowed = ["final.mp4", "thumbnail.png", "script.txt", "subtitle.srt", "metadata.json"]
    if filename not in allowed:
        raise HTTPException(status_code=403, detail="File không được phép truy cập")
    p = settings.OUTPUTS_DIR / project_id / filename
    if not p.exists():
        p = settings.PROJECTS_DIR / project_id / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(p), filename=filename)
