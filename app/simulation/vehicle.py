import math
from app.simulation.geometry import box, cylinder, rigid_body


class VehicleGenerator:
    PRESETS = {'brick_basic_car': {'mass': 3, 'wheel_radius': .42, 'speed': 3.0, 'acceleration': 1.5, 'friction': .8}}

    def create(self, preset, color):
        import bpy
        if preset not in self.PRESETS:
            raise ValueError(f'Unsupported vehicle preset: {preset}')
        bpy.ops.object.empty_add()
        self.root = bpy.context.object
        self.root.name = 'brick_vehicle'
        body = box('Brick chassis', (0,0,.72), (2.5,1.45,.45), color)
        rigid_body(body, animated=True, mass=self.PRESETS[preset]['mass'])
        parts = [body, box('Brick cabin', (-.28,0,1.18), (1.15,1.3,.48), color),
                 box('Windscreen', (.31,0,1.2), (.06,1.15,.34), 'glass'),
                 box('Front bumper', (1.3,0,.68), (.18,1.55,.19), 'white')]
        for x in (-.65, -.05, .65):
            for y in (-.42,.42):
                parts.append(cylinder('Construction stud', (x,y,.995), .13, .12, color))
        for y in (-.47,.47):
            parts.append(box('Headlamp', (1.26,y,.83), (.06,.25,.15), 'gold'))
        self.wheels = []
        for x in (-.82,.82):
            for y in (-.83,.83):
                wheel = cylinder('Rubber wheel', (x,y,.42), .42, .3, 'tire', (math.pi/2,0,0))
                hub = cylinder('Wheel hub', (0,0, .17 if y < 0 else -.17), .23, .05, 'white')
                hub.parent = wheel
                # Asymmetric spoke makes wheel rotation visible.
                spoke = box('Hub spoke', (0,.12, .2 if y < 0 else -.2), (.08,.32,.03), 'gold')
                spoke.parent = wheel
                self.wheels.append(wheel)
                parts.append(wheel)
        for part in parts:
            part.parent = self.root
        return self.root

    def animate(self, frame, x, height, pitch, time):
        self.root.location = (x,0,height)
        self.root.rotation_euler.y = pitch
        self.root.keyframe_insert('location', frame=frame)
        self.root.keyframe_insert('rotation_euler', frame=frame)
        for wheel in self.wheels:
            wheel.rotation_euler.y = -time * 3 / .42
            wheel.keyframe_insert('rotation_euler', frame=frame)

    def recover(self, checkpoint):
        """Deterministic checkpoint reset for future controlled failure choreography."""
        self.root.location = checkpoint['vehicle_state']['position']
        self.root.rotation_euler = (0, checkpoint['vehicle_state']['pitch'], 0)
