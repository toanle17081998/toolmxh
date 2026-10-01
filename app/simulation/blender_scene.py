"""Run exclusively through Blender --background --python; no Pydantic needed."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def build(payload):
    import bpy
    from app.simulation.geometry import box, cylinder, rigid_body
    from app.simulation.vehicle import VehicleGenerator
    from app.simulation.camera import CameraController
    from app.simulation.obstacles import OBSTACLES

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scenario, segment = payload['scenario'], payload['segment']
    scene.render.engine = payload['engine']
    scene.render.resolution_x, scene.render.resolution_y = payload['width'], payload['height']
    scene.render.resolution_percentage = 100
    scene.render.fps = scenario['fps']
    scene.frame_start, scene.frame_end = 1, segment['frame_count']
    scene.gravity = (0,0,-9.81)
    scene.view_settings.view_transform = 'AgX'
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = {'draft': 8, 'standard': 32, 'high': 96}[scenario['quality']]
        scene.cycles.use_denoising = True
    elif hasattr(scene, 'eevee'):
        scene.eevee.taa_render_samples = {'draft': 8, 'standard': 32, 'high': 64}[scenario['quality']]
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.72,.84,1,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6

    start_x = segment['start_state']['position'][0] - 40
    end_x = segment['end_state']['position'][0] + 40
    center, length = (start_x+end_x)/2, end_x-start_x
    floor = box('Studio floor', (center,0,-.65), (length+30,60,.4), 'floor')
    track = box('Runway', (center,0,-.2), (length,6,.4), 'track')
    rigid_body(track)
    for y in (-3.15,3.15):
        rail = box('Track edging', (center,y,.1), (length,.22,.2), 'white')
        rigid_body(rail)
    # Stable world-coordinate decoration, independent of segment seed/index.
    for i in range(math.floor(start_x/8), math.ceil(end_x/8)):
        color = ('coral','mint','gold','violet','blue')[i % 5]
        for side in (-1,1):
            h = .4 + (i % 3)*.4
            box('Toy world brick', (i*8,side*(6+i%3),h/2-.4), (2,1.5,h), color)
            cylinder('World stud', (i*8,side*(6+i%3),h-.35), .3, .12, color)
    obstacles = []
    for section in segment['sections']:
        plugin = OBSTACLES[section['type']](section)
        plugin.validate()
        plugin.createGeometry()
        plugin.configurePhysics()
        obstacles.append(plugin)
    vehicle = VehicleGenerator()
    vehicle.create(scenario['vehicle']['type'], scenario['vehicle']['color'])
    camera = CameraController(scenario['camera']['mode'], scenario['aspect_ratio']=='9:16')
    lights = []
    for location, energy, size in (((0,-6,12),1800,10), ((5,6,8),1200,8), ((-8,2,6),800,6)):
        bpy.ops.object.light_add(type='AREA')
        light = bpy.context.object
        light.data.energy, light.data.shape, light.data.size = energy, 'DISK', size
        lights.append((light,location))

    for frame in range(1, segment['frame_count']+2):
        time = (segment['start_frame'] + frame-1) / scenario['fps']
        x = time * scenario['speed']
        z, pitch = 0.0, 0.0
        for obstacle in obstacles:
            if obstacle.start <= x <= obstacle.start + obstacle.length:
                z = obstacle.height_at(x,time)
                slope = (obstacle.height_at(x+.08,time)-obstacle.height_at(x-.08,time))/.16
                pitch = -math.atan(slope)
        vehicle.animate(frame,x,z,pitch,time)
        camera.animate(frame,time,(x,0,z))
        for obstacle in obstacles:
            obstacle.configureAnimation(frame,time)
        for light, offset in lights:
            light.location = (x+offset[0],offset[1],offset[2])
            light.keyframe_insert('location',frame=frame)
    scene.frame_set(1)
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(Path(payload['output_dir'])/'frames'/'') + '/'
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(payload['output_dir'])/'scene.blend'))
    # Explicit numbering avoids Blender's default four-digit animation filenames.
    for frame in range(1, segment['frame_count']+1):
        scene.frame_set(frame)
        scene.render.filepath = str(Path(payload['output_dir'])/'frames'/f'{frame:06d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'SIMULATION_FRAME {frame}/{segment["frame_count"]}', flush=True)


if __name__ == '__main__':
    scenario_file = Path(sys.argv[sys.argv.index('--')+1])
    build(json.loads(scenario_file.read_text(encoding='utf-8')))
