"""Two-phase Bullet simulation / measured playback for backend render workers."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))


def build(payload, playback=False):
    import bpy
    from app.simulation.geometry import box, rigid_body, PALETTE
    from app.simulation.physics_vehicle import BrickVehicleFactory
    from app.simulation.physics_prototype import render
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scenario,segment = payload['scenario'],payload['segment']
    output = Path(payload['output_dir'])
    PALETTE['track'] = (.65,.67,.7,1)
    scene.render.engine = payload['engine']
    scene.render.resolution_x,scene.render.resolution_y = payload['width'],payload['height']
    scene.render.resolution_percentage = 100
    scene.render.fps = scenario['fps']
    scene.frame_start,scene.frame_end = 1,scenario['duration']*scenario['fps']
    scene.gravity = (0,0,-9.81)
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.8,.8,.8,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
    scene.view_settings.view_transform = 'AgX'
    quality = scenario['quality']
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = {'preview':8,'draft':8,'standard':32,'high':96}[quality]
        scene.cycles.use_denoising = True
    elif hasattr(scene,'eevee'):
        scene.eevee.taa_render_samples = {'preview':8,'draft':8,'standard':32,'high':64}[quality]
    sections = scenario['sections']
    elevation = sum(s['parameters']['height'] for s in sections if s['type']=='platform_drop')
    spawn_height = elevation
    cursor = -10
    def runway(start,end,height):
        if end<=start:
            return
        obj = box('track_surface',( (start+end)/2,0,height-.3),(end-start,5,.6),'track')
        rigid_body(obj)
    for section in sections:
        runway(cursor,section['start'],elevation)
        if section['type']=='platform_drop':
            elevation -= section['parameters']['height']
            cursor = section['start']+section['length']
        elif section['type']=='gap':
            cursor = section['start']+section['length']
        else:
            cursor = section['start']
        from app.simulation.obstacles import OBSTACLES
        plugin = OBSTACLES[section['type']](section)
        plugin.validate()
        plugin.createGeometry()
        for obj in plugin.objects:
            obj.location.z += elevation
        plugin.configurePhysics()
    runway(cursor,scenario['duration']*scenario['speed']+30,elevation)
    floor = box('safety_floor',(scenario['duration'],0,-3.3),(scenario['duration']*5+40,30,.6),'track')
    rigid_body(floor)
    factory = BrickVehicleFactory()
    factory.create(position=(0,0,spawn_height+.85),color=scenario['vehicle']['color'],speed=scenario['speed']*payload.get('traction_scale',1))
    world = scene.rigidbody_world
    world.substeps_per_frame,world.solver_iterations = 8,60
    world.point_cache.frame_start,world.point_cache.frame_end = 1,scene.frame_end
    physical = [factory.chassis,*factory.wheels]
    telemetry_path = output/'telemetry.json'
    if not playback:
        samples,events,checkpoints = [],[],[]
        previous = None
        stuck_frames = 0
        failure_reason = None
        for frame in range(1,scene.frame_end+1):
            scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            matrices = [obj.evaluated_get(graph).matrix_world.copy() for obj in physical]
            sample = [{'position':list(m.translation),'rotation':list(m.to_quaternion())} for m in matrices]
            position = sample[0]['position']
            if not all(math.isfinite(v) and abs(v)<10000 for obj in sample for v in obj['position']+obj['rotation']):
                raise RuntimeError('Non-finite/extreme physics transforms')
            if position[2]<-2 or abs(position[1])>4:
                failure_reason = failure_reason or 'Vehicle left the intended track'
            if position[2]<-5:
                raise RuntimeError('Vehicle fell through the safety-floor collider')
            if samples and any(math.dist(left['position'],right['position'])>5 for left,right in zip(samples[-1],sample)):
                raise RuntimeError('Explosive rigid-body step')
            if previous:
                velocity = [(position[i]-previous[i])*scenario['fps'] for i in range(3)]
                stuck_frames = stuck_frames+1 if abs(velocity[0])<.08 else 0
                if stuck_frames>scenario['fps']*4:
                    failure_reason = failure_reason or 'Vehicle is stuck'
                # Detect downward motion arrest, not only a bouncing landing.
                if velocity[2]>-.2 and previous_velocity[2]<-.8 and (not events or (frame-1)/scenario['fps']-events[-1]['time']>.4):
                    events.append({'time':(frame-1)/scenario['fps'],'type':'landing'})
            else:
                velocity = [0,0,0]
            for section in sections:
                if previous and previous[0]<section['start']+section['length']<=position[0]:
                    checkpoints.append({'frame':frame,'obstacle':section['type'],'bodies':sample,'velocity':velocity})
            samples.append(sample)
            previous,previous_velocity = position,velocity
        if scene.frame_end>scenario['fps']*3 and samples[-1][0]['position'][0]<2:
            failure_reason = failure_reason or 'Vehicle did not progress'
        goal = max((s['start']+s['length'] for s in sections),default=2)
        outcome = 'failure' if failure_reason else ('success' if samples[-1][0]['position'][0]>=goal else 'incomplete')
        result = {'experiment_id':0,'kind':'obstacle_course','label':'Obstacle course',
                  'outcome':outcome,
                  'metrics':{'distance':samples[-1][0]['position'][0], 'failure_reason':failure_reason,
                             'wheel_count':len(factory.wheels),'goal_x':goal}}
        telemetry_path.write_text(json.dumps({'validated':True,'fingerprint':payload['fingerprint'],
                                             'samples':samples,'events':events,'checkpoints':checkpoints,'result':result}),encoding='utf-8')
        print('PHYSICS_VALIDATED',flush=True)
        return
    telemetry = json.loads(telemetry_path.read_text(encoding='utf-8'))
    if not telemetry['validated'] or telemetry['fingerprint']!=payload['fingerprint'] or len(telemetry['samples'])!=scenario['duration']*scenario['fps']:
        raise RuntimeError('Refusing unvalidated playback')
    samples = telemetry['samples'][segment['start_frame']:segment['start_frame']+segment['frame_count']]
    scene.frame_end = segment['frame_count']
    render(scene,factory,physical,samples,output,portrait=scenario['aspect_ratio']=='9:16',
           camera_mode=scenario['camera']['mode'],start_time=segment['start_frame']/scenario['fps'],
           static_anchor=telemetry['samples'][0][0]['position'])


if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    build(json.loads(Path(args[-1]).read_text(encoding='utf-8')),playback='--playback' in args)
