import math
from .base import BaseObstacle


class MovingPlatformObstacle(BaseObstacle):
    def createGeometry(self):
        from app.simulation.geometry import box
        self.platform = box('Lift platform', (self.start + self.length/2, 0, -.15), (self.length, self.section['width'], .3), self.parameters['color'])
        self.objects = [self.platform]
        return self.objects

    def height_at(self, x, time):
        u = self.fraction(x)
        return self.parameters['height'] * math.sin(math.pi*u)**2

    def configureAnimation(self, frame, time):
        # The platform rises beneath the approaching car and returns to the runway.
        self.platform.location.z = self.height_at(time * 3, time) - .15
        self.platform.keyframe_insert('location', frame=frame)
