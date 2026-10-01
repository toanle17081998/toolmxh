"""Opt-in preview examples using the real project/physics/audio/MP4 pipeline."""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


async def main(args):
    from app.config import settings
    from app.simulation.models import SimulationConfig
    from app.simulation.service import SimulationVideoService
    settings.BLENDER_CLEANUP = not args.keep_scenes
    examples = [('design_comparison',20,3),('improve_retry',20,3),('destruction',6,1),('ball_race',6,1),('chain_reaction',6,1)]
    for family,duration,trials in examples:
        if args.only and family not in args.only:
            continue
        config = SimulationConfig(content_type=family,idea_id=f'{family}:0',duration=duration,
                                  trial_count=trials,seed=42,quality='preview')
        result = await SimulationVideoService().generate_video(f'content_{family}_42',config)
        print(result['final_video_path'],result['qc_result'],flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--only',nargs='+')
    parser.add_argument('--keep-scenes',action='store_true')
    asyncio.run(main(parser.parse_args()))
