import math
import random
import secrets
from app.simulation.models import Scenario, SegmentPlan, WorldState
from app.simulation.track import SimulationTrackGenerator, difficulty_at
from app.simulation.obstacles import OBSTACLES
from app.simulation.motion import vehicle_pose as _vehicle_pose


def vehicle_pose(sections, x, time):
    return _vehicle_pose([s.model_dump() if hasattr(s,'model_dump') else s for s in sections],x,time)


class ScenarioGenerator:
    def generate(self, config):
        seed = config.seed if config.seed is not None else secrets.randbits(32)
        rng = random.Random(seed)
        color = rng.choice(['red', 'blue', 'yellow', 'green', 'orange']) if config.color == 'random' else config.color
        sections = SimulationTrackGenerator().generate(config.duration, config.difficulty, config.theme, seed,
                                                       config.repetition_window, config.repetition_limit)
        events = []
        for section in sections:
            events.append({'time': (section.start + section.length * .5) / 3,
                           'type': 'mechanical' if section.type in ('hammer', 'rotating_bar', 'moving_platform') else 'wheels',
                           'obstacle': section.type})
            if section.type == 'ramp':
                events.append({'time': (section.start + section.length * .85) / 3, 'type': 'landing'})
        events.append({'time': max(0, config.duration - .6), 'type': 'success'})

        def state_at(frame):
            time = frame / config.fps
            height, pitch = vehicle_pose(sections, time * 3, time)
            return WorldState(vehicle_color=color, difficulty=difficulty_at(time / config.duration, config.difficulty),
                              progress=time / config.duration, position=(time * 3, 0, height),
                              pitch=pitch, wheel_angle=-time * 3 / .42, time=time)

        segments = []
        total_frames = config.duration * config.fps
        for index, frame in enumerate(range(0, total_frames, config.segment_seconds * config.fps), 1):
            count = min(config.segment_seconds * config.fps, total_frames - frame)
            start, end = state_at(frame), state_at(frame + count)
            context = [s for s in sections if s.start + s.length >= start.position[0] - 25 and s.start <= end.position[0] + 25]
            checkpoint_frames = list(range(frame, frame + count, config.fps * 5))
            segments.append(SegmentPlan(index=index, seed=(seed + index * 104729) % 2**32,
                                        start_frame=frame, frame_count=count, start_state=start, end_state=end,
                                        sections=context, checkpoints=[{'frame': f, 'seed': seed, 'vehicle_state': state_at(f).model_dump()} for f in checkpoint_frames]))
        return Scenario(theme=config.theme, duration=config.duration, aspect_ratio=config.aspect_ratio,
                        fps=config.fps, seed=seed, quality=config.quality, vehicle={'type': config.vehicle, 'color': color, 'size': 'medium'},
                        environment={'type': config.theme, 'lighting': 'studio', 'time': 'day'},
                        camera={'mode': 'dynamic_follow', 'distance': 8, 'height': 4},
                        audio={'music': config.music, 'sound_effects': config.sound_effects, 'engine_sound': config.engine_sound},
                        sections=sections, events=events, segments=segments)
