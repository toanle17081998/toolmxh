"""Live quality cases: python -m app.health.quality --case all [--plan-only]."""
import argparse
import asyncio
import json
from pathlib import Path

from app.config import settings
from app.engines.composer import VideoComposer
from app.engines.subtitle import SubtitleEngine
from app.engines.timeline import TimelineEngine
from app.health.generation import HealthVisualGenerator
from app.health.models import HealthCharacterBible, HealthScenePlan
from app.health.planner import HealthVisualPlanner, save_json
from app.models.script import SceneScript, StructuredScript
from app.providers.image.gemini_imagen import GeminiImagenProvider
from app.providers.image.real_media import RealVisualMediaEngine
from app.providers.llm.factory import get_llm_provider
from app.providers.tts.factory import get_tts_provider
from app.providers.video.veo import GoogleVeoVideoProvider
from app.providers.video.wan import WanVideoProvider


QUALITY_SCRIPTS = {
    "liver": (
        "What happens to the liver when excessive alcohol is consumed?",
        [
            "Gan khỏe mạnh xử lý các chất được đưa đến từ máu.",
            "Khi uống rượu, cồn được hấp thu vào máu và đưa đến gan.",
            "Gan chuyển hóa cồn; uống quá nhiều rượu khiến gan phải làm việc nhiều hơn.",
            "Các sản phẩm chuyển hóa của cồn có thể gây stress và làm tổn thương tế bào gan.",
            "Theo thời gian, uống quá nhiều rượu có thể khiến chất béo tích tụ trong gan.",
        ],
    ),
    "kidney": (
        "How kidneys filter waste from blood",
        [
            "Máu được đưa đến hai quả thận để bắt đầu quá trình lọc.",
            "Thận lọc chất thải và nước dư thừa từ máu; các chất cần thiết được tái hấp thu.",
            "Máu sau khi được lọc trở lại tuần hoàn, còn chất thải đi vào nước tiểu.",
        ],
    ),
    "stomach": (
        "What happens inside the stomach during digestion",
        [
            "Thức ăn đi qua thực quản vào dạ dày.",
            "Dạ dày tiết axit và enzyme để giúp tiêu hóa thức ăn.",
            "Dạ dày co bóp, trộn thức ăn với dịch vị, rồi chuyển hỗn hợp xuống ruột non.",
        ],
    ),
}


def quality_script(case):
    title, narration = QUALITY_SCRIPTS[case]
    return StructuredScript(title=title, hook=narration[0], target_duration=len(narration) * 6,
                            language="vi", scenes=[
                                SceneScript(id=index, narration=text, visual="", estimated_duration=6.0)
                                for index, text in enumerate(narration, 1)
                            ])


async def run_case(case, directory: Path, llm, plan_only=False, reuse_plan=False,
                   image_model="gemini-2.5-flash-image", video_model="veo-3.1-fast-generate-preview"):
    directory.mkdir(parents=True, exist_ok=True)
    script = quality_script(case)
    save_json(directory / "script.json", script.model_dump())
    stage = "semantic_planning"
    report = {"case": case, "planning_accepted": False, "actual_video_generated": False}
    try:
        if reuse_plan:
            bible = HealthCharacterBible.model_validate_json((directory / "health_character_bible.json").read_text(encoding="utf-8"))
            plans = {}
            for scene in script.scenes:
                debug = json.loads((directory / "health_debug" / f"scene_{scene.id:03d}.json").read_text(encoding="utf-8"))
                if debug.get("narration") != scene.narration or not debug.get("accepted"):
                    raise RuntimeError("Cannot reuse a health plan with changed narration or a rejected score")
                plan = HealthScenePlan.model_validate(debug["attempts"][-1])
                if not plan.relevance.accepted:
                    raise RuntimeError("Cannot reuse a rejected health plan")
                plans[scene.id] = plan
        else:
            storyboard, bible, plans = await HealthVisualPlanner(llm).plan(script, directory)
            save_json(directory / "storyboard.json", storyboard.model_dump())
        report = {"case": case, "planning_accepted": True,
                  "scores": {scene_id: plan.relevance.total for scene_id, plan in plans.items()},
                  "actual_video_generated": False}
        save_json(directory / "quality_report.json", report)
        if plan_only:
            return report
        image = GeminiImagenProvider(model=image_model) if settings.GEMINI_API_KEY else RealVisualMediaEngine()
        video = GoogleVeoVideoProvider(model=video_model) if settings.GEMINI_API_KEY else WanVideoProvider()
        generator = HealthVisualGenerator(llm, image, video, image_model="explicit")
        width, height = 540, 960
        stage = "character_reference_generation"
        await generator.generate_references(bible, directory, width, height)
        stage = "narration_generation"
        timeline = await TimelineEngine(get_tts_provider(voice="namminh")).build_timeline(script, directory, voice="namminh")
        videos = []
        for timing in timeline.scenes:
            stage = f"scene_{timing.scene_id:03d}_generation"
            scene = next(scene for scene in script.scenes if scene.id == timing.scene_id)
            videos.append(await generator.generate_scene(
                scene.narration, plans[scene.id], bible, directory / "scenes" / f"{scene.id:03d}",
                directory, timing.duration, width, height,
            ))
        subtitles = directory / "subtitle.ass"
        SubtitleEngine().generate_ass(timeline, str(subtitles), platform="tiktok", title=script.title)
        final = directory / "final.mp4"
        stage = "final_composition"
        await VideoComposer().compose_video(videos, timeline.master_narration_path, str(subtitles),
                                             str(final), width=width, height=height,
                                             total_duration=timeline.total_duration)
        await generator._run_ffmpeg(["-i", str(final), "-f", "null", "-"])
        report.update({"actual_video_generated": True, "final_video": str(final),
                       "duration": timeline.total_duration})
        save_json(directory / "quality_report.json", report)
        return report
    except Exception as error:
        report.update({"failed_stage": stage, "error_type": type(error).__name__, "error": str(error)})
        save_json(directory / "quality_report.json", report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["all", *QUALITY_SCRIPTS], default="all")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--llm-model", default="gemini-2.5-flash")
    parser.add_argument("--image-model", default="gemini-2.5-flash-image")
    parser.add_argument("--video-model", default="veo-3.1-fast-generate-preview")
    parser.add_argument("--reuse-plan", action="store_true", help="Reuse only previously accepted plans with identical narration")
    parser.add_argument("--output", type=Path, default=settings.OUTPUTS_DIR / "health_quality")
    args = parser.parse_args()
    async def run():
        llm = get_llm_provider(model=args.llm_model)
        failed = []
        for case in QUALITY_SCRIPTS if args.case == "all" else [args.case]:
            try:
                report = await run_case(case, args.output / case, llm, args.plan_only, args.reuse_plan,
                                        args.image_model, args.video_model)
                print(f"{case}: prompt scores {report['scores']}; actual video: {report['actual_video_generated']}")
            except Exception as error:
                failed.append(case)
                print(f"{case}: BLOCKED ({type(error).__name__}); see {args.output / case / 'quality_report.json'}")
        return 1 if failed else 0
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
