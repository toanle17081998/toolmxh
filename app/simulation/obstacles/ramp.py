import math
from .base import BaseObstacle


class RampObstacle(BaseObstacle):
    def createGeometry(self):
        from app.simulation.geometry import wedge
        h = self.parameters['height']
        self.objects = [wedge('Launch ramp', self.start, self.length * .5, self.section['width'], h, self.parameters['color'])]
        return self.objects

    def height_at(self, x, time):
        u, h = self.fraction(x), self.parameters['height']
        if u < .5:
            return 2 * h * u
        if u < .85:
            v = (u - .5) / .35
            return h * (1 - v) + .55 * math.sin(math.pi * v)
        return 0.0
