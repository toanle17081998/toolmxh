import math


class CameraController:
    def __init__(self, mode='dynamic_follow', portrait=False):
        import bpy
        bpy.ops.object.camera_add()
        self.camera = bpy.context.object
        self.mode, self.portrait = mode, portrait
        self.camera.data.lens = 38 if not portrait else 30
        self.camera.data.clip_end = 500
        bpy.context.scene.camera = self.camera

    def animate(self, frame, time, position):
        from mathutils import Vector
        x, y, z = position
        # Slowly orbit between rear-quarter and side views; global time preserves segment continuity.
        angle = .5 + .22 * math.sin(time * .12)
        distance = 10 if not self.portrait else 12
        self.camera.location = (x-distance*math.cos(angle), -distance*math.sin(angle)-4, z+6)
        target = Vector((x+1.9, 0, z+.7))
        self.camera.rotation_euler = (target-self.camera.location).to_track_quat('-Z','Y').to_euler()
        self.camera.keyframe_insert('location', frame=frame)
        self.camera.keyframe_insert('rotation_euler', frame=frame)
