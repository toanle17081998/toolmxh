import math
from .base import BaseObstacle


class StairsObstacle(BaseObstacle):
    def createGeometry(self):
        from app.simulation.geometry import box
        steps, stride = 8, self.length / 8
        self.objects = []
        for i in range(steps):
            h = self.parameters['height'] * min(i + 1, steps - i) / 4
            self.objects.append(box('Toy stair', (self.start + (i+.5)*stride, 0, h/2), (stride, self.section['width'], h), self.parameters['color']))
        return self.objects

    def height_at(self, x, time):
        u = self.fraction(x)
        if u == 0 or u == 1:
            return 0.0
        # Wheels climb a softened staircase instead of teleporting at each riser.
        step = u * 8
        i = int(step)
        a = min(i, 8-i) / 4
        b = min(i+1, 7-i) / 4
        blend = (1 - math.cos(math.pi * (step-i))) / 2
        return self.parameters['height'] * (a + (b-a)*blend)
