import math
from .base import BaseObstacle


class HammerObstacle(BaseObstacle):
    def createGeometry(self):
        import bpy
        from app.simulation.geometry import box
        x = self.start + self.length / 2
        bpy.ops.object.empty_add(location=(x, 0, 4.8))
        self.pivot = bpy.context.object
        arm = box('Pendulum arm', (0, 0, -1.4), (.22, .22, 2.8), 'metal')
        head = box('Swinging hammer', (0, 0, -2.8), (1.1, 1.4, .7), self.parameters['color'])
        arm.parent = head.parent = self.pivot
        self.objects = [arm, head, box('Hammer arch', (x, 0, 5), (.45, 6, .35), 'violet')]
        self.objects.extend(box('Hammer support', (x, y, 2.5), (.4, .4, 5), 'violet') for y in (-2.8, 2.8))
        return self.objects

    def configureAnimation(self, frame, time):
        self.pivot.rotation_euler.x = .8 * math.sin(time * self.parameters['speed'] * 2)
        self.pivot.keyframe_insert('rotation_euler', frame=frame)
