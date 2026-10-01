import math
from .base import ExperimentWorld, support
from app.simulation.geometry import finish, cylinder, rigid_body
from app.simulation.physics_vehicle import active


class BallWorld(ExperimentWorld):
    race = False

    def create(self):
        import bpy
        angle = self.challenge['slope']
        deck = support('gravity_runway',(6,0,2),(16,5,.3))
        deck.rotation_euler.y = angle
        support('ball_landing',(18,0,-.3),(40,20,.6))
        for side in (-1,1):
            rail = support('ball_rail',(6,side*2.5,2.3),(16,.18,.8))
            rail.rotation_euler.y = angle
        balls = []
        for index in range(3 if self.race else 1):
            vary_friction = self.challenge.get('ball_variant')=='friction'
            radius = (.35,.46,.6)[index] if self.race and not vary_friction else .46
            y = (index-1)*1.3 if self.race else 0
            z = 2+.15/math.cos(angle)+6*math.tan(angle)+radius+.05
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=radius,location=(0,y,z))
            obj = finish(bpy.context.object,'gravity_ball',('red','blue','green')[index],0)
            active(obj,.4,'SPHERE')
            obj.rigid_body.friction = (.02,.2,1.2)[index] if self.race and vary_friction else .55
            balls.append(obj)
        if self.challenge.get('pegs'):
            for x,y in ((3,.6),(5,-.6),(7,.6)):
                z = 2+.15/math.cos(angle)+(6-x)*math.tan(angle)
                peg = cylinder('brick_peg',(x,y,z+.3),.22,.6,'gold')
                rigid_body(peg)
        self.simple_factory(balls)
        return self.finish()

    def evaluate(self,samples,fps):
        finishes = []
        for ball in range(len(self.bodies)):
            frame = next((i for i,s in enumerate(samples) if s[ball]['position'][0]>=9),None)
            finishes.append({'ball':ball+1,'finish_time':round(frame/fps,3) if frame is not None else None})
        ranked = sorted((f for f in finishes if f['finish_time'] is not None),key=lambda f:f['finish_time'])
        groups = []
        for finished in ranked:
            if groups and groups[-1]['finish_time']==finished['finish_time']:
                groups[-1]['balls'].append(finished['ball'])
            else:
                groups.append({'finish_time':finished['finish_time'],'balls':[finished['ball']]})
        return {'outcome':'success' if len(ranked)==len(self.bodies) else 'failure',
                'metrics':{'finish_times':finishes,'ranking_groups':groups,'ball_count':len(self.bodies)}}


class BallRaceWorld(BallWorld):
    race = True
