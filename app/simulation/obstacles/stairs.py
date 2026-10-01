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
        if x <= self.start or x >= self.start+self.length:
            return 0.0
        i = min(7,int(u*8))
        return self.parameters['height'] * min(i+1,8-i) / 4
