"""Opt-in real Bullet validation across renderable content families."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


async def main(args):
    from app.config import settings
    from app.simulation.content import FAMILIES
    from app.simulation.models import SimulationConfig
    from app.simulation.director import SimulationDirector
    from app.simulation.blender_renderer import BlenderRenderer,run_process
    renderer = BlenderRenderer()
    root = settings.OUTPUTS_DIR/'content_physics_smoke'
    root.mkdir(parents=True,exist_ok=True)
    reports = []
    names = [f.id for f in FAMILIES if f.world is not None and f.id!='obstacle_course'] if args.all else args.content_types
    for name in names:
        scenario = SimulationDirector().generate(SimulationConfig(content_type=name,idea_id=f'{name}:0',duration=20,trial_count=3,seed=42))
        for trial in scenario.experiments:
            directory = root/name/str(trial.id)
            directory.mkdir(parents=True,exist_ok=True)
            segment = next(s for s in scenario.segments if s.experiment_id==trial.id)
            payload = {'scenario':scenario.model_dump(),'experiment':trial.model_dump(),'segment':segment.model_dump(),
                       'width':480,'height':270,'engine':settings.BLENDER_RENDER_ENGINE,'output_dir':str(directory),
                       'fingerprint':renderer.fingerprint(scenario,trial.id)}
            path = directory/'scenario.json'
            path.write_text(json.dumps(payload),encoding='utf-8')
            await run_process([renderer.check_available(),'--background','--factory-startup','--python-exit-code','1',
                               '--python',Path('app/simulation/experiment_scene.py').resolve(),'--',path],directory/'physics.log',settings.BLENDER_TIMEOUT)
            telemetry = json.loads((directory/'telemetry.json').read_text(encoding='utf-8'))
            assert len(telemetry['samples'])==trial.frame_count
            assert telemetry['validated']
            bumpers = [body for body in telemetry['body_definitions'] if body['name'].startswith('bumper_collision')]
            if telemetry['expected_wheels']:
                assert len(bumpers)==2, 'Visual bumpers need corresponding physical colliders'
                assert all(abs(body['dimensions'][0]-trial.design.bumper_length)<.0001 for body in bumpers)
                if name!='durability':
                    assert max(sample[0]['position'][0] for sample in telemetry['samples'])>2, 'Vehicle did not actually drive before attempting its challenge'
            reports.append(telemetry['result'])
            following = next((candidate for candidate in scenario.experiments if candidate.id==trial.id+1),None)
            if following:
                from app.simulation.experiments import refine_next_trial
                refine_next_trial(trial,following,telemetry['result'])
            print(name,trial.id,telemetry['result']['outcome'],telemetry['result']['metrics'],flush=True)
    (root/'report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--all',action='store_true')
    parser.add_argument('--content-types',nargs='+',default=['design_comparison','destruction','durability','ball_race','chain_reaction'])
    asyncio.run(main(parser.parse_args()))
