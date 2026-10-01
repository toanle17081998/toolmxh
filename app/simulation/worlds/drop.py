import math
from .base import ExperimentWorld, support, up_component


class DropWorld(ExperimentWorld):
    def create(self):
        support('drop_floor',(0,0,-.3),(40,24,.6))
        self.vehicle(self.challenge['drop_height'],speed=0)
        return self.finish()

    def evaluate(self,samples,fps):
        velocities = [(right[0]['position'][2]-left[0]['position'][2])*fps for left,right in zip(samples,samples[1:])]
        landed = samples[-1][0]['position'][2]<1.5
        upright = up_component(samples[-1][0]['rotation'])>.5
        return {'outcome':'success' if landed and upright else 'failure',
                'metrics':{'drop_height':self.challenge['drop_height'],'peak_fall_speed':round(abs(min(velocities,default=0)),3),
                           'landed_upright':upright,'final_tilt_degrees':round(math.degrees(math.acos(max(-1,min(1,up_component(samples[-1][0]['rotation']))))),1),
                           'wheel_count':len(self.factory.wheels)}}
