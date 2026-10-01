from .base import ExperimentWorld, support
from app.simulation.geometry import box
from app.simulation.physics_vehicle import active


class ImpactWorld(ExperimentWorld):
    def create(self):
        support('impact_floor',(12,0,-.3),(50,18,.6))
        self.vehicle()
        for row in range(3):
            for column in range(5):
                obj = box('impact_brick',(5,(column-2)*.45,row*.34+.17),(.45,.43,.32),'blue' if row%2 else 'gold')
                active(obj,.12,'BOX')
                self.targets.append(obj)
        return self.finish()

    def evaluate(self,samples,fps):
        start = len(self.bodies)-len(self.targets)
        moved = sum(((final['position'][0]-first['position'][0])**2+(final['position'][1]-first['position'][1])**2)**.5>.3
                    for first,final in zip(samples[0][start:],samples[-1][start:]))
        return {'outcome':'success' if moved>=3 else 'failure',
                'metrics':{'displaced_blocks':moved,'total_blocks':len(self.targets),'wheel_count':len(self.factory.wheels)}}
