"""Headless physical trial orchestration; world behavior lives in plugins."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))


def build(payload, playback=False):
    import bpy
    from app.simulation.geometry import PALETTE
    from app.simulation.worlds import WORLDS
    from app.simulation.physics_prototype import render
    scenario,trial,segment = payload['scenario'],payload['experiment'],payload['segment']
    output = Path(payload['output_dir'])
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    PALETTE['track'] = (.65,.67,.7,1)
    scene = bpy.context.scene
    scene.render.engine = payload['engine']
    scene.render.resolution_x,scene.render.resolution_y = payload['width'],payload['height']
    scene.render.resolution_percentage,scene.render.fps = 100,scenario['fps']
    scene.frame_start,scene.frame_end = 1,trial['frame_count']-trial['assembly_frames']
    scene.gravity = (0,0,-9.81)
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.8,.8,.8,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
    scene.view_settings.view_transform = 'AgX'
    samples = {'preview':8,'draft':8,'standard':32,'high':64}[scenario['quality']]
    if scene.render.engine=='CYCLES':
        scene.cycles.samples,scene.cycles.use_denoising = samples,True
    elif hasattr(scene,'eevee'):
        scene.eevee.taa_render_samples = samples
    world = WORLDS[trial['challenge']['world']](trial,scenario)
    factory,bodies = world.create()
    scene.rigidbody_world.substeps_per_frame = 8
    scene.rigidbody_world.solver_iterations = 60
    scene.rigidbody_world.point_cache.frame_start = 1
    scene.rigidbody_world.point_cache.frame_end = scene.frame_end
    path = output/'telemetry.json'
    if not playback:
        telemetry = solve(scene,world,bodies,payload)
        path.write_text(json.dumps(telemetry),encoding='utf-8')
        print('EXPERIMENT_VALIDATED '+json.dumps(telemetry['result']),flush=True)
        return
    telemetry = json.loads(path.read_text(encoding='utf-8'))
    if not telemetry.get('validated') or telemetry['fingerprint']!=payload['fingerprint'] or len(telemetry['samples'])!=trial['frame_count']:
        raise RuntimeError('Invalid or incompatible experiment telemetry')
    offset = segment['start_frame']-trial['start_frame']
    samples = telemetry['samples'][offset:offset+segment['frame_count']]
    if len(samples)!=segment['frame_count']:
        raise RuntimeError('Experiment slice does not match segment')
    scene.frame_end = segment['frame_count']
    annotation = None
    if scenario.get('show_labels'):
        annotation = {'label':f'TRIAL {trial["id"]}/{len(scenario["experiments"])}  |  {trial["label"]}',
                      'outcome':telemetry['result']['outcome'].upper(),'trial_frames':trial['frame_count'],
                      'metrics':telemetry['result']['metrics']}
    render(scene,factory,bodies,samples,output,portrait=scenario['aspect_ratio']=='9:16',
           camera_mode=scenario['camera']['mode'],static_anchor=telemetry['samples'][0][0]['position'],
           assembly_frames=trial['assembly_frames'],local_start=offset,annotation=annotation)


def solve(scene,world,bodies,payload):
    import bpy
    trial,scenario = payload['experiment'],payload['scenario']
    samples,events = [],[]
    body_definitions = [{'name':body.name,'mass':body.rigid_body.mass,'shape':body.rigid_body.collision_shape,
                         'dimensions':list(body.dimensions)} for body in bodies]
    previous = None
    impacted = set()
    for frame in range(1,scene.frame_end+1):
        scene.frame_set(frame)
        graph = bpy.context.evaluated_depsgraph_get()
        matrices = [body.evaluated_get(graph).matrix_world.copy() for body in bodies]
        sample = [{'position':list(m.translation),'rotation':list(m.to_quaternion())} for m in matrices]
        if not all(math.isfinite(v) and abs(v)<1000 for body in sample for v in body['position']+body['rotation']):
            raise RuntimeError('Non-finite/extreme experiment transforms')
        if previous:
            steps = [math.dist(left['position'],right['position']) for left,right in zip(previous,sample)]
            if max(steps)>5:
                raise RuntimeError('Explosive rigid-body step; refusing final render')
            time = (trial['start_frame']+trial['assembly_frames']+frame-1)/scenario['fps']
            velocity = (sample[0]['position'][2]-previous[0]['position'][2])*scenario['fps']
            if velocity>-.2 and previous_velocity<-.8 and (not events or time-events[-1]['time']>.35):
                events.append({'time':time,'type':'landing','experiment_id':trial['id']})
            target_start = len(bodies)-len(world.targets)
            moving_targets = [index for index in range(target_start,len(bodies)) if steps[index]*scenario['fps']>.8 and index not in impacted]
            if moving_targets and (not events or time-events[-1]['time']>.2):
                events.append({'time':time,'type':'landing','experiment_id':trial['id']})
                impacted.update(moving_targets)
        else:
            velocity = 0
        samples.append(sample)
        previous,previous_velocity = sample,velocity
    result = world.evaluate(samples,scenario['fps'])
    design = trial['design'] if world.factory.wheels else {'name':trial['label'],'subject_type':scenario['vehicle']['type'],
                                                          'parameters':trial['challenge']}
    result.update(experiment_id=trial['id'],label=trial['label'],kind=trial['kind'],
                  design=design,controlled_variable=trial['controlled_variable'],
                  refinement_reason=trial.get('refinement_reason'))
    samples = [samples[0]]*trial['assembly_frames']+samples
    return {'validated':True,'fingerprint':payload['fingerprint'],'sample_start_frame':trial['start_frame'],
            'samples':samples,'events':events,'checkpoints':[],'result':result,
            'body_definitions':body_definitions,
            'expected_wheels':len(world.factory.wheels)}


if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    build(json.loads(Path(args[-1]).read_text(encoding='utf-8')),playback='--playback' in args)
