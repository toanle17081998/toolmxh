import argparse
import asyncio
import json
import logging
import uuid
from app.config import settings
from app.core.state_manager import ProjectStateManager
from app.simulation.models import SimulationConfig
from app.simulation.service import SimulationVideoService


def main():
    parser = argparse.ArgumentParser(description='Headless simulation video generator and real render smoke test')
    parser.add_argument('--smoke', action='store_true', help='Render six seconds with an obstacle in two draft segments')
    parser.add_argument('--duration', type=int, default=60)
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--aspect-ratio', choices=['16:9','9:16'], default='16:9')
    parser.add_argument('--quality', choices=['draft','standard','high'], default='standard')
    parser.add_argument('--fps', type=int, choices=[24,30], default=30)
    parser.add_argument('--segment-seconds', type=int, default=30)
    parser.add_argument('--blender-path', default=None)
    parser.add_argument('--project-id', default=None)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--keep-scenes', action='store_true')
    args = parser.parse_args()
    if args.resume and not args.project_id:
        parser.error('--resume requires --project-id')
    if args.blender_path:
        settings.BLENDER_PATH = args.blender_path
    if args.keep_scenes:
        settings.BLENDER_CLEANUP = False
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    project_id = args.project_id or ('sim_smoke_' if args.smoke else 'sim_') + uuid.uuid4().hex[:8]
    if args.resume:
        config = ProjectStateManager(project_id).load_state().config.simulation
        if config is None:
            parser.error('Project is not a simulation video')
    else:
        config = SimulationConfig(duration=6 if args.smoke else args.duration, seed=args.seed,
                                  aspect_ratio=args.aspect_ratio, quality='draft' if args.smoke else args.quality,
                                  fps=args.fps, segment_seconds=3 if args.smoke else args.segment_seconds)
    result = asyncio.run(SimulationVideoService().generate_video(project_id,config))
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
