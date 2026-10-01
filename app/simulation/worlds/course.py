from .base import ExperimentWorld, support
from app.simulation.geometry import wedge, box, rigid_body


class CourseWorld(ExperimentWorld):
    def create(self):
        h = self.challenge.get('drop_height',1.5)
        support('survival_start',(-3,0,h-.3),(14,5,.6))
        support('survival_landing',(14,0,-.3),(20,5,.6))
        ramp = wedge('survival_ramp',8,3,5,.4,'track')
        rigid_body(ramp)
        for i in range(4):
            step = box('survival_step',(13+i*.65,0,.08*(i+1)),(.65,5,.16*(i+1)),'track')
            rigid_body(step)
        support('survival_floor',(10,0,-3.3),(60,24,.6))
        self.vehicle(h)
        return self.finish()

    def evaluate(self,samples,fps):
        return self.crossing(samples,fps,.5)
