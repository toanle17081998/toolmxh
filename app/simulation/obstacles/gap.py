from .base import BaseObstacle


class GapObstacle(BaseObstacle):
    def createGeometry(self):
        from app.simulation.geometry import box
        gap = self.section['gap']
        self.objects = [box('gap_landing', (self.start+(gap+self.length)/2,0,-.3),
                            (self.length-gap,self.section['width'],.6),'track')]
        return self.objects

    def validate(self):
        super().validate()
        if not 0<self.section['gap']<=1:
            raise ValueError('Crawler gap must be between zero and one unit')
        return True
