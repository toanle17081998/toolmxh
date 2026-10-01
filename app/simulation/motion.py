"""Shared wheel-support motion, usable in the app and Blender's own Python."""
import math
from app.simulation.obstacles import OBSTACLES


def vehicle_pose(sections, x, time):
    obstacles = [OBSTACLES[s['type']](s) for s in sections]
    for obstacle in obstacles:
        if obstacle.section['type']=='moving_platform' and obstacle.start <= x <= obstacle.start+obstacle.length:
            return obstacle.height_at(x,time), 0.0

    def support(position):
        for obstacle in obstacles:
            if obstacle.start <= position <= obstacle.start+obstacle.length:
                return obstacle.height_at(position,time)
        return 0.0

    front, rear = support(x+.82), support(x-.82)
    pitch = -math.asin(max(-.8,min(.8,(front-rear)/1.64)))
    # Compensate for the wheel centers rotating around the vehicle's root.
    height = (front+rear)/2 + .42*(1-math.cos(pitch))
    return height,pitch
