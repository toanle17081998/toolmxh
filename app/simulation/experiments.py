"""Experiment planning and measured-outcome refinements, separate from Blender."""
import math
import random
from app.simulation.content import CONTENT_FAMILIES
from app.simulation.models import ExperimentPlan, SegmentPlan, VehicleDesign, WorldState


DESIGNS = (
    VehicleDesign(name='Wide car', body_width=1.6, wheel_track=2.1),
    VehicleDesign(name='Narrow crawler', body_width=.76, wheel_track=1.16, body_height=.75),
    VehicleDesign(name='Six-wheel crawler', body_width=.9, wheel_track=1.26, wheelbase=2.3, wheel_count=6),
)


def plan_experiments(config, idea, seed):
    family = CONTENT_FAMILIES[idea['content_type']]
    rng = random.Random(seed)
    total = config.duration * config.fps
    count = max(config.trial_count, math.ceil(config.duration / 10))
    if total < count * config.fps * 4:
        raise ValueError('Each experiment needs at least four seconds; reduce trial_count or increase duration')
    base_challenge = {'world': family.world, 'width': {1:2.2,2:1.68,3:1.5}[config.difficulty], 'span': 4.0, 'elevation': 1.8,
                      'style': 'beam', 'goal_x': 8.0, 'seed': seed}
    plans, segments, cursor = [], [], 0
    template = int(idea['id'].rsplit(':', 1)[1])
    for index in range(count):
        frames = total // count + (index < total % count)
        challenge = dict(base_challenge)
        design = DESIGNS[index % len(DESIGNS)].model_copy(deep=True)
        controlled = 'design'
        kind = family.id
        if kind == 'improve_retry':
            design = DESIGNS[0].model_copy(deep=True)
        if kind == 'parameter_test':
            controlled = ('wheel_radius', 'wheelbase', 'mass')[template]
            values = {'wheel_radius': (.32, .46, .65), 'wheelbase': (1.1, 1.56, 2.6), 'mass': (1.5, 2.8, 6)}
            design = DESIGNS[1].model_copy(update={controlled: values[controlled][index % 3], 'name': f'{controlled} {values[controlled][index % 3]}'})
        if kind == 'destruction':
            controlled = 'bumper_length' if template == 2 else 'mass'
            value = (.16, .3, .5)[index % 3] if controlled == 'bumper_length' else (1.5, 3, 7)[index % 3]
            design = VehicleDesign(name=f'{controlled} {value}', **{controlled: value})
        if kind == 'durability':
            controlled = 'drop_height'
            challenge['drop_height'] = (1.4, 2.5, 3.5)[index % 3]
            design = VehicleDesign(name=f'Drop {challenge["drop_height"]}m')
            if template == 1:
                controlled = 'body_height'
                challenge['drop_height'] = 2.5
                design.body_height = (.65, 1, 1.35)[index % 3]
                design.name = f'Body height {design.body_height}'
            elif template == 2:
                controlled = 'wheel_count'
                challenge['drop_height'] = 2.5
                design.wheel_count = (4, 6)[index % 2]
                design.name = f'{design.wheel_count} wheels'
        if kind == 'bridge_engineering':
            controlled = 'bridge_structure'
            challenge['style'] = ('beam', 'planks', 'reinforced')[index % 3]
            challenge['width'] = 2.4
            design = VehicleDesign(name=challenge['style'], mass=5)
        if kind == 'cargo_balance':
            controlled = 'payload_height' if template == 1 else 'payload_mass'
            design = DESIGNS[1].model_copy(deep=True)
            design.payload_mass = 3 if template == 1 else (1, 3, 5)[index % 3]
            design.payload_height = (1.1, 1.5, 1.9)[index % 3] if template == 1 else 1.15
            design.name = f'{controlled} {getattr(design, controlled)}'
        if kind == 'time_trial':
            challenge['width'] = 2.8
        if kind == 'limit_test':
            controlled = 'gap'
            challenge.update(style='gap', span=min(4,.65+index*.625), width=2.6)
            challenge['goal_x'] = 4 + challenge['span'] + 1
            design = VehicleDesign(name=f'Gap {challenge["span"]}m')
        if kind == 'chain_reaction':
            controlled = 'spacing' if template == 1 else 'chain_length'
            challenge.update(spacing=(.32, .4, .65)[index % 3] if template == 1 else .36,
                             domino_count=(10, 14, 18)[index % 3] if template != 1 else 14)
            design = VehicleDesign(name=f'Domino trial {index + 1}')
        if kind in ('marble_run', 'ball_race'):
            challenge.update(slope=rng.uniform(.18, .23), pegs=kind == 'marble_run',
                             ball_variant='friction' if template==2 else 'radius')
            design = VehicleDesign(name='Marble run' if kind == 'marble_run' else 'Three-ball race')
        if kind == 'survival':
            challenge['drop_height'] = 1.5
            challenge['goal_x'] = 15
        plans.append(ExperimentPlan(id=index + 1, start_frame=cursor, frame_count=frames,
                                    assembly_frames=min(config.fps, frames // 5) if family.world not in ('ball', 'ball_race', 'domino') else 0,
                                    kind=kind, label=design.name, design=design, challenge=challenge,
                                    controlled_variable=controlled))
        def state(frame):
            subject_type = {'ball':'gravity_ball','ball_race':'gravity_balls','domino':'construction_domino'}.get(family.world,'brick_crawler')
            return WorldState(vehicle_type=subject_type, vehicle_color=config.color if config.color != 'random' else 'red',
                              time=frame/config.fps, progress=frame/total)
        for offset in range(0, frames, config.segment_seconds * config.fps):
            length = min(frames - offset, config.segment_seconds * config.fps)
            segments.append(SegmentPlan(index=len(segments)+1, seed=seed, start_frame=cursor+offset, frame_count=length,
                                        start_state=state(cursor+offset), end_state=state(cursor+offset+length),
                                        sections=[], checkpoints=[], experiment_id=index+1))
        cursor += frames
    return plans, segments


def refine_next_trial(previous, next_trial, result):
    """A candidate change follows measured failure/success, never a promised win."""
    if previous.kind != 'improve_retry':
        return
    design = previous.design.model_copy(deep=True)
    if result['outcome'] == 'failure':
        design.wheel_track = max(1.1, design.wheel_track * .78)
        design.body_width = max(.6, min(design.body_width, design.wheel_track - .36))
        design.body_height = max(.6, design.body_height * .85)
        reason = 'Previous crossing failed: narrow the axle/body and lower the center of mass'
    elif result['outcome'] == 'success':
        design.mass = max(1, design.mass * .85)
        reason = 'Previous crossing succeeded: test a lighter candidate on the same bridge'
    else:
        reason = 'Previous trial reached its time limit: keep the candidate rather than invent a design failure'
    design.name = f'Refined design {next_trial.id}'
    next_trial.design = VehicleDesign.model_validate(design.model_dump())
    next_trial.label, next_trial.refinement_reason = design.name, reason


def summarize_results(results):
    successful = [result for result in results if result['outcome']=='success']
    timed = [r for r in successful if r['metrics'].get('finish_time') is not None]
    fastest_time = min((r['metrics']['finish_time'] for r in timed),default=None)
    summary = {'successful_trials':[r['experiment_id'] for r in successful],
            'failed_trials':[r['experiment_id'] for r in results if r['outcome']=='failure'],
            'incomplete_trials':[r['experiment_id'] for r in results if r['outcome']=='incomplete'],
            'fastest_trials':[r['experiment_id'] for r in timed if r['metrics']['finish_time']==fastest_time],
            'fastest_time':fastest_time,'basis':'measured physics outcomes; equal frame times are ties'}
    limits = [r for r in results if r['kind']=='limit_test']
    if limits:
        first_failure = next((r for r in limits if r['outcome']=='failure'),None)
        summary['first_failed_limit'] = first_failure['metrics'].get('gap') if first_failure else None
    return summary
