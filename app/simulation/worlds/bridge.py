from .base import ExperimentWorld, support
from app.simulation.geometry import box
from app.simulation.physics_vehicle import active


class BridgeWorld(ExperimentWorld):
    def create(self):
        import bpy
        entry,span,elevation = 4,self.challenge['span'],self.challenge['elevation']
        width,style = self.challenge['width'],self.challenge['style']
        support('bridge_start',(-3,0,elevation-.3),(14,5,.6))
        support('bridge_exit',(entry+span+10,0,elevation-.3),(20,5,.6))
        support('landing_floor',(10,0,-.3),(60,24,.6))
        if style=='beam':
            support('bridge_beam',(entry+span/2,0,elevation-.16),(span,width,.32))
        elif style in ('planks','reinforced'):
            planks = []
            anchors = [support('bridge_anchor',(entry-.05,0,elevation-.15),(.1,width,.3))]
            for index in range(8):
                obj = box('construction_bridge_plank',(entry+(index+.5)*span/8,0,elevation-.12),(span/8-.01,width,.24),'white')
                active(obj,.25,'BOX')
                planks.append(obj)
            anchors.append(support('bridge_anchor',(entry+span+.05,0,elevation-.15),(.1,width,.3)))
            connected = [anchors[0],*planks,anchors[1]]
            for index,(left,right) in enumerate(zip(connected,connected[1:])):
                bpy.ops.object.empty_add(type='PLAIN_AXES',location=(entry+index*span/8,0,elevation-.12))
                joint = bpy.context.object
                bpy.ops.rigidbody.constraint_add()
                c = joint.rigid_body_constraint
                c.type,c.object1,c.object2 = 'FIXED',left,right
                c.disable_collisions,c.use_breaking = True,True
                c.breaking_threshold = .7 if style=='planks' else 8
                self.constraints.append(joint)
            self.targets = planks
        self.vehicle(elevation)
        return self.finish()

    def evaluate(self,samples,fps):
        result = self.crossing(samples,fps,self.challenge['elevation']+.5)
        if self.challenge['style']=='gap':
            result['metrics']['gap'] = self.challenge['span']
        if self.targets:
            start = len(self.bodies)-len(self.targets)
            result['metrics']['fallen_bridge_members'] = sum(s['position'][2]<self.challenge['elevation']-.5 for s in samples[-1][start:])
        return result
