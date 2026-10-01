from abc import ABC, abstractmethod


class BaseObstacle(ABC):
    def __init__(self, section):
        self.section = section
        self.start, self.length = section['start'], section['length']
        self.parameters = section['parameters']
        self.objects = []

    @abstractmethod
    def createGeometry(self):
        """Create original Blender geometry and return its objects."""

    def configurePhysics(self):
        from app.simulation.geometry import rigid_body
        for obj in self.objects:
            rigid_body(obj, animated=True)

    def configureAnimation(self, frame, time):
        """Static obstacles require no animated transforms."""

    def getEntryPoint(self):
        return self.start, 0, 0

    def getExitPoint(self):
        return self.start + self.length, 0, 0

    def validate(self):
        if self.length < 6 or not 0 < self.parameters.get('height', 1) <= 2:
            raise ValueError('Invalid obstacle dimensions')
        return True

    def cleanup(self):
        import bpy
        for obj in self.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        self.objects.clear()

    def height_at(self, x, time):
        return 0.0

    def fraction(self, x):
        return max(0.0, min(1.0, (x - self.start) / self.length))
