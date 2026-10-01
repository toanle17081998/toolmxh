"""Small world contract shared by physical experiment plugins (Blender only)."""
import math
from types import SimpleNamespace
from app.simulation.geometry import box, rigid_body
from app.simulation.physics_vehicle import BrickVehicleFactory


def support(name, center, size):
    obj = box(name,center,size,'track')
    rigid_body(obj)
    return obj


def up_component(quaternion):
    w,x,y,z = quaternion
    return 1-2*(x*x+y*y)


class ExperimentWorld:
    def __init__(self, trial, scenario):
        self.trial, self.scenario = trial, scenario
        self.challenge = trial['challenge']
        self.targets = []
        self.constraints = []

    def create(self):
        raise NotImplementedError

    def vehicle(self, elevation=0, speed=None):
        self.factory = BrickVehicleFactory()
        design = self.trial['design']
        self.factory.create(position=(0,0,elevation+.35+design['wheel_radius']+.04),
                            color=self.scenario['vehicle']['color'],
                            speed=self.scenario['speed'] if speed is None else speed,design=design)
        self.bodies = [self.factory.chassis,*self.factory.wheels,*self.factory.extra_bodies]

    def simple_factory(self, bodies):
        self.bodies = bodies
        self.factory = SimpleNamespace(chassis=bodies[0],wheels=[],extra_bodies=[],constraints=[])

    def finish(self):
        self.factory.constraints.extend(self.constraints)
        self.bodies.extend(self.targets)
        return self.factory,self.bodies

    def crossing(self, samples, fps, minimum_height=.8):
        goal = self.challenge.get('goal_x',8)
        crossing = next((i for i,s in enumerate(samples) if s[0]['position'][0]>=goal
                         and s[0]['position'][2]>=minimum_height and up_component(s[0]['rotation'])>.5),None)
        metrics = {'distance':round(max(s[0]['position'][0] for s in samples),3),
                   'finish_time':round(crossing/fps,3) if crossing is not None else None,
                   'max_tilt_degrees':round(max(math.degrees(math.acos(max(-1,min(1,up_component(s[0]['rotation']))))) for s in samples),1),
                   'wheel_count':len(self.factory.wheels)}
        if crossing is not None:
            outcome = 'success'
        else:
            last = samples[-1][0]
            recent = samples[max(0,len(samples)-fps)][0]
            failed = last['position'][2]<minimum_height or up_component(last['rotation'])<.5 or abs(last['position'][0]-recent['position'][0])<.1
            outcome = 'failure' if failed else 'incomplete'
        return {'outcome':outcome,'metrics':metrics}

    def evaluate(self, samples, fps):
        return self.crossing(samples,fps)
