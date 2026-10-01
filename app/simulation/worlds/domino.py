from .base import ExperimentWorld, support, up_component
from app.simulation.geometry import box
from app.simulation.physics_vehicle import active


class DominoWorld(ExperimentWorld):
    def create(self):
        support('domino_floor',(4,0,-.3),(24,18,.6))
        dominoes = []
        for index in range(self.challenge['domino_count']):
            obj = box('construction_domino',(index*self.challenge['spacing'],0,.62),(.14,.65,1.2),('red','blue','yellow')[index%3])
            # Preserve the initial lean as a real unstable physical pose.
            active(obj,.12,'BOX')
            if index==0:
                obj.rotation_euler.y = .3
            dominoes.append(obj)
        self.simple_factory(dominoes)
        return self.finish()

    def evaluate(self,samples,fps):
        fallen = sum(up_component(body['rotation'])<.5 for body in samples[-1])
        return {'outcome':'success' if fallen==len(self.bodies) else 'failure',
                'metrics':{'fallen_dominoes':fallen,'total_dominoes':len(self.bodies),'spacing':self.challenge['spacing']}}
