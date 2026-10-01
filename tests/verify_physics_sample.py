"""Verify real-render telemetry, seam replay and extract frames from final MP4."""
import argparse
import asyncio
import json
import math
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


async def verify(project_id):
    from app.config import settings, get_ffmpeg_binary
    from app.simulation.media import validate_media
    from app.simulation.blender_renderer import run_process
    root = settings.PROJECTS_DIR/project_id
    export = settings.OUTPUTS_DIR/project_id
    scenario = json.loads((root/'scenario.json').read_text(encoding='utf-8'))
    telemetry = [json.loads((root/'segments'/f'{s["index"]:03d}'/'telemetry.json').read_text(encoding='utf-8')) for s in scenario['segments']]
    for left,right in zip(telemetry,telemetry[1:]):
        assert right['samples'][:len(left['samples'])]==left['samples'], 'Physics warm-up differs across segment seam'
    samples = telemetry[-1]['samples']
    assert len(samples)==scenario['duration']*scenario['fps']
    assert all(len(frame)==5 for frame in samples), 'Expected chassis plus exactly four wheels'
    assert all(math.isfinite(v) for frame in samples for body in frame for v in body['position'])
    distance = samples[-1][0]['position'][0]-samples[0][0]['position'][0]
    assert distance>scenario['duration'], 'Vehicle did not progress at a believable speed'
    angular_travel = []
    for wheel in range(1,5):
        angle = sum(2*math.acos(min(1,abs(sum(a*b for a,b in zip(left[wheel]['rotation'],right[wheel]['rotation']))))) for left,right in zip(samples,samples[1:]))
        assert angle>distance/.46*.6, 'Wheel rotation missing or too slow'
        angular_travel.append(angle)
    qc = await validate_media(export/'final.mp4',480,270,scenario['duration'],scenario['fps'],require_audio=True)
    for second in (0,3,4,9,10,13,17,19):
        if second>=scenario['duration']:
            continue
        await run_process([get_ffmpeg_binary(),'-y','-ss',second,'-i',export/'final.mp4',
                           '-frames:v','1',export/f'acceptance_{second:02d}.png'],export/'frame_extract.log',120)
    report = {'qc':qc,'wheel_count':4,'distance':distance,'wheel_angular_travel':angular_travel,
              'continuous_physics_prefix':True,'measured_checkpoints':len(telemetry[-1]['checkpoints']),
              'landing_events':len(telemetry[-1]['events'])}
    (export/'physics_acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('project_id')
    asyncio.run(verify(parser.parse_args().project_id))
