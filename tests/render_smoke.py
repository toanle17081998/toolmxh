"""Opt-in real Blender integration: python tests/render_smoke.py --blender-path PATH."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


async def verify_plugins(binary):
    from app.config import settings
    from app.simulation.models import SimulationConfig
    from app.simulation.scenario import ScenarioGenerator
    from app.simulation.blender_renderer import BlenderRenderer
    from app.simulation.media import validate_media
    if binary:
        settings.BLENDER_PATH = binary
    config = SimulationConfig(duration=20,seed=42,quality='preview')
    scenario = ScenarioGenerator().generate(config)
    renderer = BlenderRenderer()
    root = settings.OUTPUTS_DIR/'simulation_plugin_smoke'
    # Prime one authoritative validated trajectory, then sample solved crossings.
    prime = scenario.segments[0].model_copy(deep=True)
    prime.frame_count = 3
    await renderer.render_segment(scenario,prime,root/'segments'/'prime',480,270)
    telemetry = json.loads((root/'segments'/'prime'/'telemetry.json').read_text(encoding='utf-8'))
    for name in ('platform_drop','ramp','stairs','gap'):
        section = next(section for section in scenario.sections if section.type==name)
        # Sample three frames at the crossing, with global time unchanged.
        segment = next(s.model_copy(deep=True) for s in scenario.segments if section in s.sections)
        segment.start_frame = min(range(len(telemetry['samples'])-3),key=lambda frame:abs(telemetry['samples'][frame][0]['position'][0]-(section.start+section.length/2)))
        segment.frame_count = 3
        directory = root/'segments'/name
        output = await renderer.render_segment(scenario,segment,directory,480,270)
        result = await validate_media(output,480,270,.1,30)
        assert result['frames']==3
        print(f'{name}: real Blender render OK',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--blender-path',default=None)
    args = parser.parse_args()
    asyncio.run(verify_plugins(args.blender_path))
