"""Standalone physics acceptance prototype. Run with Blender --background."""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def run(args):
    import bpy
    from app.simulation.geometry import box, rigid_body, PALETTE
    from app.simulation.physics_vehicle import BrickVehicleFactory
    from app.simulation.camera import CameraController
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    PALETTE['track'] = (.65,.67,.7,1)
    PALETTE['floor'] = (.83,.84,.86,1)
    scene = bpy.context.scene
    scene.render.engine = args.engine
    scene.render.resolution_x, scene.render.resolution_y = 480,270
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.frame_start, scene.frame_end = 1,args.duration*30
    scene.gravity = (0,0,-9.81)
    scene.world.color = (.5,.5,.5)
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.8,.8,.8,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
    scene.view_settings.view_transform = 'AgX'
    if args.engine == 'CYCLES':
        scene.cycles.samples = 8
        scene.cycles.use_denoising = True
    elif hasattr(scene, 'eevee'):
        scene.eevee.taa_render_samples = 8
    ground = box('lower_landing_platform', (12,0,-.3), (44,12,.6), 'track')
    rigid_body(ground)
    upper = box('upper_platform_drop', (-3,0,1.5), (18,5,3), 'track')
    rigid_body(upper)
    factory = BrickVehicleFactory()
    factory.create(speed=args.speed)
    world = scene.rigidbody_world
    world.substeps_per_frame = 8
    world.solver_iterations = 60
    world.point_cache.frame_start, world.point_cache.frame_end = 1,scene.frame_end
    physical = [factory.chassis,*factory.wheels]
    if args.playback:
        telemetry = json.loads((output/'telemetry.json').read_text(encoding='utf-8'))
        if not telemetry['report']['valid'] or telemetry.get('speed')!=args.speed:
            raise RuntimeError('Prototype playback requires valid, compatible telemetry')
        samples = telemetry['samples']
        if len(samples)!=scene.frame_end:
            raise RuntimeError('Prototype telemetry duration mismatch')
    else:
        samples = simulate(scene, physical, output, args.speed)
    if args.simulate_only:
        return
    if not args.playback:
        raise RuntimeError('Render in a fresh Blender process with --playback after --simulate-only')
    render(scene, factory, physical, samples, output)


def simulate(scene, physical, output, speed):
    import bpy
    samples = []
    for frame in range(1,scene.frame_end+1):
        scene.frame_set(frame)
        graph = bpy.context.evaluated_depsgraph_get()
        transforms = [obj.evaluated_get(graph).matrix_world.copy() for obj in physical]
        samples.append([{'position':list(m.translation), 'rotation':list(m.to_quaternion())} for m in transforms])
    positions = [s[0]['position'] for s in samples]
    report = {'wheel_count':len(physical)-1,'frames':len(samples), 'start':positions[0], 'end':positions[-1],
              'max_x':max(p[0] for p in positions),'min_z':min(p[2] for p in positions),
              'max_pitch':max(abs(math.asin(max(-1,min(1,2*(s[0]['rotation'][0]*s[0]['rotation'][2]-s[0]['rotation'][3]*s[0]['rotation'][1]))))) for s in samples)}
    report['valid'] = all(math.isfinite(v) and abs(v)<500 for s in samples for obj in s for v in obj['position']) and report['max_x']>7 and report['min_z']<1.5 and report['min_z']>-.5
    report['wheel_start_end'] = [samples[0][1],samples[-1][1]]
    (output/'telemetry.json').write_text(json.dumps({'report':report,'samples':samples,'speed':speed}),encoding='utf-8')
    print(json.dumps(report), flush=True)
    if not report['valid']:
        raise RuntimeError('Physics validation failed; inspect telemetry before rendering')
    return samples


def render(scene, factory, physical, samples, output, portrait=False, camera_mode='dynamic_follow', start_time=0, static_anchor=None,
           assembly_frames=0, local_start=0, annotation=None):
    import bpy
    from app.simulation.camera import CameraController
    # Replay measured Bullet results for render-time random access. No invented driving path.
    bpy.ops.rigidbody.world_remove()
    for joint in factory.constraints:
        bpy.data.objects.remove(joint,do_unlink=True)
    for obj in physical:
        bpy.context.view_layer.objects.active = obj
        if obj.rigid_body:
            bpy.ops.rigidbody.object_remove()
        obj.rotation_mode = 'QUATERNION'
    camera = CameraController(camera_mode,portrait)
    parts = {obj:obj.location.copy() for obj in bpy.context.scene.objects if obj.parent in physical and obj not in physical}
    label = None
    if annotation:
        bpy.ops.object.text_add()
        label = bpy.context.object
        label.name = 'experiment_label'
        label.parent = camera.camera
        label.location = (-2 if portrait else -3.3, 3.2 if portrait else 1.7, -10)
        label.data.size = .17
        mat = bpy.data.materials.new('Experiment label ink')
        mat.use_nodes = True
        shader = mat.node_tree.nodes['Principled BSDF']
        shader.inputs['Base Color'].default_value = (.025,.03,.04,1)
        shader.inputs['Emission Color'].default_value = (.025,.03,.04,1)
        shader.inputs['Emission Strength'].default_value = 1
        label.data.materials.append(mat)
    lights = []
    for offset,energy,size in (((0,-5,10),1600,8),((3,5,8),1100,7)):
        bpy.ops.object.light_add(type='AREA')
        light = bpy.context.object
        light.data.energy,light.data.size = energy,size
        lights.append((light,offset))
    for frame,sample in enumerate(samples,1):
        from mathutils import Vector
        phase = min(1,(local_start+frame)/assembly_frames) if assembly_frames else 1
        ease = phase*phase*(3-2*phase)
        for obj,transform in zip(physical,sample):
            obj.location = transform['position']
            if obj in factory.wheels and phase<1:
                obj.location += Vector((0,3*(1-ease)*(1 if obj.location.y>=0 else -1),1.5*(1-ease)))
            obj.rotation_quaternion = transform['rotation']
            obj.keyframe_insert('location',frame=frame)
            obj.keyframe_insert('rotation_quaternion',frame=frame)
        for index,(part,target) in enumerate(parts.items()):
            part.location = target+Vector(((index%3-1)*(1-ease),0,(1.2+index%4*.25)*(1-ease)))
            part.keyframe_insert('location',frame=frame)
        camera.animate(frame,start_time+(frame-1)/scene.render.fps,sample[0]['position'])
        x,y,z = sample[0]['position']
        offsets = {'dynamic_follow':(-3,-10,5),'follow':(-7,-8,5),'side_follow':(0,-11,4),
                   'low_follow':(-3,-10,3),'front_obstacle':(6,-9,5),'top_down':(0,-.5,13),'static':(-3,-10,5)}
        offset = offsets[camera_mode]
        scale = 1.25 if portrait else 1
        camera.camera.location = tuple(sample[0]['position'][i]+offset[i]*scale for i in range(3))
        if camera_mode=='static':
            anchor = static_anchor or samples[0][0]['position']
            camera.camera.location = (anchor[0]+5,anchor[1]-16,anchor[2]+9)
        camera.camera.rotation_euler = (Vector((x+1,y,z)) - camera.camera.location).to_track_quat('-Z','Y').to_euler()
        camera.camera.keyframe_insert('location',frame=frame)
        camera.camera.keyframe_insert('rotation_euler',frame=frame)
        for light,offset in lights:
            light.location = tuple(sample[0]['position'][i]+offset[i] for i in range(3))
            light.keyframe_insert('location',frame=frame)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'scene.blend'))
    frames = output/'frames'
    frames.mkdir(exist_ok=True)
    scene.render.image_settings.file_format = 'PNG'
    for frame in range(1,scene.frame_end+1):
        scene.frame_set(frame)
        if label:
            label.data.body = annotation['label']
            if local_start+frame>annotation['trial_frames']-scene.render.fps:
                label.data.body += '\n'+annotation['outcome']
                metrics = annotation['metrics']
                if metrics.get('finish_time') is not None:
                    label.data.body += f'  {metrics["finish_time"]:.2f}s'
                elif 'displaced_blocks' in metrics:
                    label.data.body += f'  {metrics["displaced_blocks"]}/{metrics["total_blocks"]} blocks'
                elif 'fallen_dominoes' in metrics:
                    label.data.body += f'  {metrics["fallen_dominoes"]}/{metrics["total_dominoes"]} dominoes'
        scene.render.filepath = str(frames/f'{frame:06d}.png')
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--duration',type=int,default=10)
    parser.add_argument('--speed',type=float,default=2.2)
    parser.add_argument('--engine',default='BLENDER_EEVEE_NEXT')
    parser.add_argument('--simulate-only',action='store_true')
    parser.add_argument('--playback',action='store_true', help='Render validated Bullet telemetry in a fresh process')
    run(parser.parse_args(sys.argv[sys.argv.index('--')+1:]))
