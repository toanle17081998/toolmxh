"""Decode actual content MP4s, verify trial telemetry and extract acceptance frames."""
import argparse
import asyncio
import json
import math
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


async def verify(project_id):
    from app.config import settings,get_ffmpeg_binary
    from app.simulation.models import SimulationConfig
    from app.simulation.blender_renderer import run_process
    from app.simulation.media import validate_media
    root,export = settings.PROJECTS_DIR/project_id,settings.OUTPUTS_DIR/project_id
    state = json.loads((root/'project.json').read_text(encoding='utf-8'))
    config = SimulationConfig.model_validate(state['config']['simulation'])
    scenario = json.loads((root/'scenario.json').read_text(encoding='utf-8'))
    assert len(scenario['results'])==len(scenario['experiments'])
    results = []
    for trial in scenario['experiments']:
        segments = [segment for segment in scenario['segments'] if segment['experiment_id']==trial['id']]
        telemetry = [json.loads((root/'segments'/f'{s["index"]:03d}'/'telemetry.json').read_text(encoding='utf-8')) for s in segments]
        assert all(t['samples']==telemetry[0]['samples'] for t in telemetry), 'Trial slices do not share a trajectory'
        data = telemetry[0]
        assert data['validated'] and len(data['samples'])==trial['frame_count']
        bodies = len(data['samples'][0])
        assert all(len(frame)==bodies for frame in data['samples'])
        assert all(math.isfinite(v) for frame in data['samples'] for body in frame for v in body['position']+body['rotation'])
        if data['expected_wheels']:
            assert data['expected_wheels']==trial['design']['wheel_count']
        results.append(data['result'])
        for offset in (.4, 2.5, trial['frame_count']/scenario['fps']-.5):
            time = trial['start_frame']/scenario['fps']+offset
            await run_process([get_ffmpeg_binary(),'-y','-ss',time,'-i',export/'final.mp4','-frames:v','1',
                               export/f'trial_{trial["id"]}_{offset:.1f}.png'],export/'frame_extract.log',120)
    qc = await validate_media(export/'final.mp4',*config.dimensions(),scenario['duration'],scenario['fps'],require_audio=True)
    report = {'content_type':scenario['content_type'],'qc':qc,'trials':results,'geometry_body_count_consistent':True}
    (export/'content_acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(project_id,scenario['content_type'],qc['frames'],'frames',[(r['label'],r['outcome']) for r in results])


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('project_ids',nargs='+')
    args = parser.parse_args()
    for project in args.project_ids:
        asyncio.run(verify(project))
