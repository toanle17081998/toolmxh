import math
import random
from app.simulation.models import TrackSection
from app.simulation.selection import ObstacleSelector
from app.simulation.obstacles import OBSTACLES


def difficulty_at(progress, difficulty):
    if progress < .2:
        return 1
    if progress < .5:
        return min(2, difficulty)
    return min(3, difficulty + 1)


def validateTrack(sections, track_length, vehicle_length=2.6, vehicle_width=1.8):
    previous_end = vehicle_length / 2 + 1
    for section in sections:
        values = (section.start, section.length, section.width, section.gap)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Non-finite track geometry')
        if section.type not in OBSTACLES:
            raise ValueError(f'Unknown obstacle: {section.type}')
        if section.start < previous_end or section.start + section.length > track_length:
            raise ValueError('Obstacle overlap, invalid spawn, or track boundary')
        if section.width < vehicle_width + .6 or section.width > 6 or section.length < 6:
            raise ValueError('Unreachable section or invalid track width')
        if section.gap < 0 or section.gap > 1.5:
            raise ValueError('Impossible gap')
        OBSTACLES[section.type](section.model_dump()).validate()
        previous_end = section.start + section.length + vehicle_length
    return True


class SimulationTrackGenerator:
    def generate(self, duration, difficulty, theme, seed, window=8, limit=2):
        rng = random.Random(seed)
        selector = ObstacleSelector(rng, OBSTACLES, window, limit)
        track_length, cursor, sections = duration * 3.0, 5.0, []
        while cursor + 12 < track_length - 3:
            level = difficulty_at(cursor / track_length, difficulty)
            length = rng.uniform(9, 12)
            sections.append(TrackSection(
                type=selector.choose(level, 'brick_basic_car', theme, int(cursor / 90)),
                start=cursor, length=length, width=5.6 - level * .2, difficulty=level,
                parameters={'height': rng.uniform(.7, 1.0) + level * .18,
                            'speed': rng.uniform(.5, .9) + level * .1,
                            'direction': rng.choice([-1, 1]), 'phase': rng.uniform(0, math.tau),
                            'color': rng.choice(['coral', 'gold', 'mint', 'violet', 'blue']),
                            'hero': len(sections) % 5 == 0}))
            cursor += length + rng.uniform(6, 12)
        validateTrack(sections, track_length)
        return sections
