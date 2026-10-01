from .base import BaseObstacle


class PlatformDropObstacle(BaseObstacle):
    def createGeometry(self):
        from app.simulation.geometry import box
        self.objects = [box('drop_landing', (self.start+self.length/2,0,-.3),
                            (self.length,self.section['width'],.6),'track')]
        return self.objects

    def getEntryPoint(self):
        return self.start,0,self.parameters['height']

    def getExitPoint(self):
        return self.start+self.length,0,0
