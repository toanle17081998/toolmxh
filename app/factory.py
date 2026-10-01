import os
import json
import uuid
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.table import Table

from app.config import settings
from app.models.project import ProjectConfig, ProjectState, PipelineStage, SceneStatus
from app.models.script import StructuredScript
from app.models.storyboard import Storyboard, VisualStyleBible
from app.core.state_manager import ProjectStateManager
from app.providers.llm.factory import get_llm_provider
from app.providers.tts.factory import get_tts_provider
from app.providers.image.factory import get_image_provider
from app.providers.video.factory import get_video_provider
from app.engines.timeline import TimelineEngine
from app.engines.subtitle import SubtitleEngine
from app.engines.audio import AudioEngine
from app.engines.composer import VideoComposer
from app.qc.validator import QualityControlValidator

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(force_terminal=True, legacy_windows=False)

class VietnameseVideoFactory:
    """Orchestrator trung tâm sản xuất Video AI tiếng Việt 100% tự động."""

    def __init__(
        self,
        console_output: bool = True,
        voice: str = "charon",
        gemini_key: Optional[str] = None,
        openai_key: Optional[str] = None,
        llm_model: Optional[str] = None,
        image_model: Optional[str] = None,
        video_model: str = "wan2.1"
    ):
        self.console_output = console_output
        self.voice = voice or "namminh"
        self.llm_model = llm_model or "gemini-3.8-flash"
        self.image_model = image_model or "auto"
        self.video_model = video_model or "wan2.1"

        # Thiết lập key nếu được truyền vào
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key

        self.llm = get_llm_provider(model=self.llm_model)
        self.tts = get_tts_provider(voice=voice)
        self.image_gen = get_image_provider(model=self.image_model)
        self.video_gen = get_video_provider(preference=self.video_model)
        self.timeline_engine = TimelineEngine(self.tts)
        self.subtitle_engine = SubtitleEngine()
        self.audio_engine = AudioEngine()
        self.composer = VideoComposer()

    def log(self, message: str, style: str = "bold cyan"):
        if self.console_output:
            console.print(f"[{style}]▶ {message}[/{style}]")

    async def generate_video(
        self,
        topic: str,
        duration: int = 60,
        platform: str = "tiktok",
        language: str = "vi",
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        p_id = project_id or f"proj_{uuid.uuid4().hex[:8]}"
        config = ProjectConfig(
            project_id=p_id,
            topic=topic,
            platform=platform,
            target_duration=duration,
            language=language,
            llm_model=self.llm_model,
            image_model=self.image_model,
            video_model=self.video_model,
            voice=self.voice
        )

        state_mgr = ProjectStateManager(p_id)
        state = state_mgr.init_project_structure(config)
        p_dir = state_mgr.project_dir

        self.log(f"Khởi tạo dự án: {p_id} | Chủ đề: '{topic}' | Nền tảng: {platform}", style="bold green")

        def _get_fallback_llm(failed_llm):
            gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
            openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
            is_openai = "openai" in failed_llm.__class__.__name__.lower()
            if is_openai and gemini_key:
                from app.providers.llm.gemini import GeminiLLMProvider
                return GeminiLLMProvider(api_key=gemini_key)
            elif not is_openai and openai_key:
                from app.providers.llm.openai import OpenAILLMProvider
                return OpenAILLMProvider(api_key=openai_key)
            else:
                from app.providers.llm.offline import OfflineBrainProvider
                return OfflineBrainProvider()

        # 1. RESEARCH
        state_mgr.update_stage(PipelineStage.RESEARCH, 5.0)
        self.log(f"Đang nghiên cứu chủ đề bằng não bộ {self.llm.__class__.__name__}...")
        try:
            research_data = await self.llm.research_topic(topic)
        except Exception as e:
            self.log(f"LLM gặp sự cố ({e}), tự động chuyển sang mô hình dự phòng...", style="bold yellow")
            self.llm = _get_fallback_llm(self.llm)
            research_data = await self.llm.research_topic(topic)
        with open(p_dir / "research" / "research.json", "w", encoding="utf-8") as f:
            json.dump(research_data, f, ensure_ascii=False, indent=2)

        # 2. SCRIPT
        state_mgr.update_stage(PipelineStage.SCRIPT, 15.0)
        self.log(f"Đang xây dựng kịch bản tiếng Việt bằng {self.llm.__class__.__name__}...")
        try:
            script = await self.llm.generate_script(topic, duration, platform, language)
        except Exception as e:
            self.log(f"LLM gặp sự cố ({e}), tự động chuyển sang mô hình dự phòng...", style="bold yellow")
            self.llm = _get_fallback_llm(self.llm)
            script = await self.llm.generate_script(topic, duration, platform, language)

        # Đảm bảo cảnh cuối luôn có đoạn Outro Call-To-Action (CTA) mời theo dõi kênh
        if script.scenes:
            last_scene = script.scenes[-1]
            cta_keywords = ["theo dõi", "đăng ký", "follow", "subscribe", "bấm like", "thả tim"]
            if not any(k in last_scene.narration.lower() for k in cta_keywords):
                last_scene.narration += " Đừng quên bấm like và theo dõi kênh để đón xem những video thú vị tiếp theo nhé!"

        with open(p_dir / "script" / "script.json", "w", encoding="utf-8") as f:
            f.write(script.model_dump_json(indent=2))
        self.log(f"Kịch bản đã hoàn thành: '{script.title}' ({len(script.scenes)} scenes)", style="green")

        # 3. STORYBOARD
        state_mgr.update_stage(PipelineStage.STORYBOARD, 25.0)
        self.log(f"Đang chuyển đổi thành Storyboard bằng {self.llm.__class__.__name__}...")
        try:
            storyboard = await self.llm.generate_storyboard(script)
        except Exception as e:
            self.log(f"LLM gặp sự cố ({e}), tự động chuyển sang mô hình dự phòng...", style="bold yellow")
            self.llm = _get_fallback_llm(self.llm)
            storyboard = await self.llm.generate_storyboard(script)
        with open(p_dir / "storyboard" / "storyboard.json", "w", encoding="utf-8") as f:
            f.write(storyboard.model_dump_json(indent=2))

        # 4. VOICE GENERATION & AUDIO-FIRST TIMELINE
        state_mgr.update_stage(PipelineStage.VOICE_GENERATION, 35.0)
        self.log("Đang tổng hợp giọng đọc tiếng Việt và căn chỉnh timeline...")
        timeline = await self.timeline_engine.build_timeline(script, p_dir, voice=config.voice)
        state_mgr.init_scenes_progress(len(script.scenes))
        self.log(f"Tổng thời lượng giọng đọc thực tế: {timeline.total_duration:.2f} giây", style="green")

        # 5. SUBTITLE
        state_mgr.update_stage(PipelineStage.SUBTITLE, 45.0)
        self.log("Đang sinh phụ đề SRT và ASS Karaoke Highlight...")
        srt_path = p_dir / "subtitles" / "subtitle.srt"
        ass_path = p_dir / "subtitles" / "subtitle.ass"
        self.subtitle_engine.generate_srt(timeline, str(srt_path))
        self.subtitle_engine.generate_ass(timeline, str(ass_path), platform=platform, title=script.title)

        # 6. VISUAL GENERATION (T2I -> I2V)
        state_mgr.update_stage(PipelineStage.VISUAL_GENERATION, 55.0)
        width, height = settings.PLATFORM_RESOLUTIONS.get(platform, (1080, 1920))
        scene_video_paths: List[str] = []

        table = Table(title=f"Tiến độ sinh Visual AI: {p_id}")
        table.add_column("Scene", justify="center", style="cyan")
        table.add_column("Duration", justify="center")
        table.add_column("Status", style="magenta")

        for s_idx, scene_timing in enumerate(timeline.scenes, 1):
            scene_dir = state_mgr.get_scene_dir(s_idx)
            img_path = scene_dir / "reference.png"
            vid_path = scene_dir / "video.mp4"
            prompt_file = scene_dir / "prompt.json"

            # Tìm storyboard tương ứng
            sb_scene = next((s for s in storyboard.scenes if s.scene_id == s_idx), None)
            img_prompt = sb_scene.image_prompt if sb_scene else f"Cinematic shot of {scene_timing.narration}"
            vid_prompt = sb_scene.video_prompt if sb_scene else "Cinematic camera slow zoom in"

            # Lưu prompt metadata
            with open(prompt_file, "w", encoding="utf-8") as f:
                json.dump({
                    "scene_id": s_idx,
                    "image_prompt": img_prompt,
                    "video_prompt": vid_prompt,
                    "duration": scene_timing.duration
                }, f, ensure_ascii=False, indent=2)

            # Kiểm tra cache / resume
            if state_mgr.is_scene_completed(s_idx):
                self.log(f"Scene {s_idx:02d}/{len(timeline.scenes):02d}: Đã hoàn thành từ trước [Bỏ qua/Resume]", style="dim")
                scene_video_paths.append(str(vid_path))
                table.add_row(f"{s_idx}", f"{scene_timing.duration:.1f}s", "[green]CACHED ✓[/green]")
                continue

            # Bước A: AI Sinh ảnh tĩnh tham chiếu (T2I)
            state_mgr.update_scene_status(s_idx, SceneStatus.GENERATING_IMAGE)
            self.log(f"Scene {s_idx:02d}/{len(timeline.scenes):02d}: Đang sinh ảnh tham chiếu AI...")
            await self.image_gen.generate_image(
                prompt=img_prompt,
                output_path=str(img_path),
                width=width,
                height=height,
                seed=s_idx * 1000 + 42
            )
            state_mgr.update_scene_status(s_idx, SceneStatus.IMAGE_DONE, image_path=str(img_path))

            # Bước B: Chuyển đổi ảnh thành video điện ảnh mượt mà (I2V)
            state_mgr.update_scene_status(s_idx, SceneStatus.GENERATING_VIDEO)
            self.log(f"Scene {s_idx:02d}/{len(timeline.scenes):02d}: Đang sinh video chuyển động khớp audio ({scene_timing.duration:.2f}s)...")
            await self.video_gen.generate_image_to_video(
                image_path=str(img_path),
                prompt=vid_prompt,
                output_path=str(vid_path),
                duration_seconds=scene_timing.duration,
                width=width,
                height=height,
                seed=s_idx * 1000 + 42
            )
            state_mgr.update_scene_status(
                s_idx,
                SceneStatus.VIDEO_DONE,
                video_path=str(vid_path),
                duration=scene_timing.duration
            )
            scene_video_paths.append(str(vid_path))
            table.add_row(f"{s_idx}", f"{scene_timing.duration:.1f}s", "[bold green]GENERATED ✓[/bold green]")

        if self.console_output:
            console.print(table)

        # 7. AUDIO MIXING (Auto-Ducking)
        state_mgr.update_stage(PipelineStage.AUDIO_MIXING, 75.0)
        self.log("Đang hòa âm giọng đọc với nhạc nền Auto-Ducking...")
        mixed_audio = p_dir / "audio" / "final_mix.wav"
        await self.audio_engine.mix_audio(
            narration_wav_path=timeline.master_narration_path,
            output_wav_path=str(mixed_audio),
            total_duration=timeline.total_duration
        )

        # 8. COMPOSITING (FFmpeg master render)
        state_mgr.update_stage(PipelineStage.COMPOSITING, 85.0)
        self.log("Đang tiến hành dựng video hoàn thiện và burn phụ đề bằng FFmpeg...")
        master_mp4 = p_dir / "renders" / "master.mp4"
        final_mp4 = p_dir / "renders" / f"{platform}.mp4"
        await self.composer.compose_video(
            scene_video_paths=scene_video_paths,
            mixed_audio_path=str(mixed_audio),
            subtitle_ass_path=str(ass_path),
            output_mp4_path=str(master_mp4),
            width=width,
            height=height,
            burn_subtitles=True,
            total_duration=timeline.total_duration
        )
        # Tạo bản sao output trực tiếp cho platform
        # Tạo các bản sao artifact hoàn thiện theo đúng chuẩn đặc tả
        import shutil
        out_root_dir = settings.OUTPUTS_DIR / p_id
        out_root_dir.mkdir(parents=True, exist_ok=True)

        final_mp4 = out_root_dir / "final.mp4"
        shutil.copy(str(master_mp4), str(final_mp4))
        shutil.copy(str(master_mp4), str(p_dir / "renders" / f"{platform}.mp4"))
        shutil.copy(str(srt_path), str(out_root_dir / "subtitle.srt"))

        # Xuất thumbnail.png từ ảnh tham chiếu của scene 1
        scene1_img = state_mgr.get_scene_dir(1) / "reference.png"
        if scene1_img.exists():
            shutil.copy(str(scene1_img), str(out_root_dir / "thumbnail.png"))

        # Xuất script.txt
        with open(out_root_dir / "script.txt", "w", encoding="utf-8") as f:
            f.write(f"TIÊU ĐỀ: {script.title}\n")
            f.write(f"HOOK (3s): {script.hook}\n\n")
            for sc in script.scenes:
                f.write(f"[Cảnh {sc.id} - {sc.estimated_duration}s]\n")
                f.write(f"Thuyết minh: {sc.narration}\n")
                f.write(f"Hình ảnh: {sc.visual}\n\n")

        # 9. SOCIAL METADATA
        self.log("Đang tạo tiêu đề, mô tả và hashtag tiếng Việt chuẩn SEO...")
        metadata = await self.llm.generate_metadata(topic, script)
        with open(p_dir / "metadata" / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        with open(out_root_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # 10. QUALITY CONTROL
        state_mgr.update_stage(PipelineStage.QC, 95.0)
        self.log("Đang kiểm định chất lượng video xuất xưởng (QC Validator)...")
        qc_result = await QualityControlValidator.validate_video(str(final_mp4), width, height)

        state_mgr.update_stage(PipelineStage.COMPLETED, 100.0)
        self.log(f"HOÀN THÀNH XUẤT SẮC! File video sẵn sàng: {final_mp4}", style="bold green")

        return {
            "project_id": p_id,
            "final_video_path": str(final_mp4),
            "master_video_path": str(master_mp4),
            "duration": timeline.total_duration,
            "scenes_count": len(script.scenes),
            "qc_result": qc_result,
            "metadata": metadata,
            "script": script.model_dump(),
            "subtitle_srt": str(out_root_dir / "subtitle.srt"),
            "subtitle_ass": str(ass_path)
        }
