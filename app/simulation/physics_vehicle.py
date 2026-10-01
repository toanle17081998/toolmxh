"""Original construction-brick vehicle with Bullet-driven wheels (Blender only)."""
import math
from app.simulation.geometry import box, cylinder, rigid_body


def attach(obj, parent):
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def active(obj, mass, shape):
    import bpy
    rigid_body(obj, animated=True, mass=mass)
    obj.rigid_body.kinematic = False
    obj.rigid_body.collision_shape = shape
    obj.rigid_body.friction = 1.2
    obj.rigid_body.linear_damping = .08
    obj.rigid_body.angular_damping = .12
    bpy.context.view_layer.objects.active = obj
    # Cylinder collision proxies use local Z, so preserve their axle rotation.
    bpy.ops.object.transform_apply(location=False, rotation=shape != 'CYLINDER', scale=True)


class BrickVehicleFactory:
    wheel_radius = .46

    def brick(self, name, location, dimensions, color, parent):
        result = attach(box(name, location, dimensions, color), parent)
        nx = max(1, round(dimensions[0] / .32))
        ny = max(1, round(dimensions[1] / .32))
        for i in range(nx):
            for j in range(ny):
                position = (location[0] + (i-(nx-1)/2)*.32,
                            location[1] + (j-(ny-1)/2)*.32,
                            location[2] + dimensions[2]/2 + .045)
                attach(cylinder('construction_brick_stud', position, .095, .09, color), parent)
        return result

    def create(self, position=(0, 0, 3.85), color='red', speed=2.2, design=None):
        import bpy
        design = design or {}
        width = design.get('body_width', 1.12)
        track = design.get('wheel_track', 1.58)
        wheelbase = design.get('wheelbase', 1.56)
        height = design.get('body_height', 1)
        length = wheelbase + .69
        radius = design.get('wheel_radius', .46)
        self.wheel_radius = radius
        x, y, z = position
        chassis = box('brick_crawler_chassis', (x,y,z+.3*height), (length, width, height), 'metal')
        chassis.hide_render = True
        active(chassis, design.get('mass', 2.8), 'BOX')
        self.chassis, self.wheels, self.constraints = chassis, [], []
        self.extra_bodies = []
        attach(box('chassis_plate', position, (length,width,.22), 'metal'),chassis)
        count = max(2, round(length/.75))
        for i in range(count):
            bx = (i-(count-1)/2)*length/count*.96
            self.brick('body_brick', (x+bx,y,z+.27*height), (length/count*.85,width*.89,.32*height), color,chassis)
        for by in (-width*.357, width*.357):
            self.brick('cabin_beam',(x-.25,y+by,z+.57*height),(.96,width*.25,.25*height),color,chassis)
        self.brick('roof_plate',(x-.25,y,z+.78*height),(.96,width*.89,.12*height),color,chassis)
        bumper_length = design.get('bumper_length',.16)
        bumper_x = wheelbase/2+radius+bumper_length/2+.08 if design else length/2+.055
        for bx in (-bumper_x,bumper_x):
            size = (bumper_length,width*1.2,.2)
            attach(box('bumper_beam',(x+bx,y,z),size,'white'),chassis)
            if design:
                for side in (-1,1):
                    attach(box('bumper_connector',(x+(1 if bx>0 else -1)*(length/2+abs(bx))/2,y+side*width*.3,z),
                               (abs(bx)-length/2+.1,.12,.12),'metal'),chassis)
                collider = box('bumper_collision',(x+bx,y,z),size,'white')
                collider.hide_render = True
                active(collider,.08,'BOX')
                self.fixed_attachment(collider,(x+bx,y,z))
        axle_positions = (-wheelbase/2, 0, wheelbase/2) if design.get('wheel_count',4)==6 else (-wheelbase/2,wheelbase/2)
        for bx in axle_positions:
            attach(cylinder('axle',(x+bx,y,z-.35),.07,track+.27,'metal',(math.pi/2,0,0)),chassis)
            for by in (-track/2, track/2):
                center = (x+bx,y+by,z-.35)
                wheel = cylinder('offroad_black_tire', center, radius, .32, 'tire', (math.pi/2,0,0))
                active(wheel, .35, 'CYLINDER')
                self.wheels.append(wheel)
                outer = by + (.18 if by > 0 else -.18)
                attach(cylinder('wheel_hub',(x+bx,y+outer,z-.35),radius*.565,.05,'white',(math.pi/2,0,0)),wheel)
                attach(box('rotation_marker', (x+bx+.12,y+outer*1.01,z-.35), (.22,.07,.07), 'gold'), wheel)
                for k in range(12):
                    angle = k*math.tau/12
                    tread = box('tire_tread',(x+bx+radius*math.sin(angle),y+by,z-.35+radius*math.cos(angle)),(.12,.35,.055),'tire')
                    tread.rotation_euler.y = angle
                    attach(tread, wheel)
                for kind in ('HINGE', 'MOTOR'):
                    bpy.ops.object.empty_add(type='PLAIN_AXES', location=center)
                    joint = bpy.context.object
                    joint.name = 'wheel_' + kind.lower()
                    # Bullet motor acts on local X; hinge acts on local Z.
                    if kind == 'MOTOR':
                        joint.rotation_euler.z = math.pi/2
                    else:
                        joint.rotation_euler.x = math.pi/2
                    bpy.ops.rigidbody.constraint_add()
                    c = joint.rigid_body_constraint
                    c.type, c.object1, c.object2 = kind, chassis, wheel
                    c.disable_collisions = True
                    if kind == 'MOTOR':
                        c.use_motor_ang = True
                        c.motor_ang_target_velocity = -speed/self.wheel_radius
                        c.motor_ang_max_impulse = 2
                    self.constraints.append(joint)
        if design.get('payload_mass',0):
            center = (x,y,z+design.get('payload_height',1.15))
            payload = box('brick_payload',center,(.8,width*.8,.32),'gold')
            active(payload,design['payload_mass'],'BOX')
            self.fixed_attachment(payload,center)
        return chassis

    def fixed_attachment(self, body, center):
        import bpy
        self.extra_bodies.append(body)
        bpy.ops.object.empty_add(type='PLAIN_AXES',location=center)
        joint = bpy.context.object
        joint.name = body.name+'_fixed_joint'
        bpy.ops.rigidbody.constraint_add()
        constraint = joint.rigid_body_constraint
        constraint.type,constraint.object1,constraint.object2 = 'FIXED',self.chassis,body
        constraint.disable_collisions = True
        self.constraints.append(joint)
