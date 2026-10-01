import math
from .base import BaseObstacle


class RotatingBarObstacle(BaseObstacle):
    def createGeometry(self):
        from app.simulation.geometry import box, cylinder
        x = self.start + self.length / 2
        self.bar = box('Rotating gate', (x, 0, 2.8), (.35, self.section['width'] + .4, .35), self.parameters['color'])
        self.objects = [self.bar, cylinder('Gate axle', (x, 0, 2.8), .24, .8, 'metal', (0, math.pi/2, 0))]
        return self.objects

    def configureAnimation(self, frame, time):
        crossing_time = (self.start + self.length/2) / 3
        self.bar.rotation_euler.x = self.parameters['direction'] * self.parameters['speed'] * (time-crossing_time)
        self.bar.keyframe_insert('rotation_euler', frame=frame)
