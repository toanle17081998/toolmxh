"""Frame-bounded planning for the physically solved construction-brick course."""
import random
import secrets
from app.simulation.models import Scenario, SegmentPlan, WorldState, TrackSection


class SimulationDirector:
    def generate(self, config):
        seed = config.seed if config.seed is not None else secrets.randbits(32)
        rng = random.Random(seed)
        color = rng.choice(['red','blue','yellow','green','orange']) if config.color == 'random' else config.color
        from app.simulation.content import SimulationIdeaGenerator
        ideas = SimulationIdeaGenerator()
        if config.idea_id:
            idea = ideas.resolve(config.idea_id, seed)
        else:
            idea = ideas.generate(seed, config.content_type, count=1)[0]
        if idea['content_type'] != 'obstacle_course':
            from app.simulation.experiments import plan_experiments
            experiments, segments = plan_experiments(config, idea, seed)
            audio = self.audio(config)
            if idea['world'] in ('ball', 'ball_race', 'domino'):
                audio['engine_sound'] = False
            subject_type = {'ball':'gravity_ball','ball_race':'gravity_balls','domino':'construction_domino'}.get(idea['world'],'brick_crawler')
            return Scenario(schema_version=3,theme='minimal_gray_track',duration=config.duration,
                            aspect_ratio=config.aspect_ratio,fps=config.fps,seed=seed,quality=config.quality,
                            vehicle={'type':subject_type,'color':color},environment={'lighting':'studio_soft'},
                            camera={'mode':config.camera_style},audio=audio,speed=2.2,sections=[],events=[],
                            segments=segments,content_type=idea['content_type'],idea=idea,experiments=experiments,
                            show_labels=config.show_labels)
        from app.simulation.track import SimulationTrackGenerator
        sections = SimulationTrackGenerator().generate(config.duration, config.difficulty, config.theme, seed)
        def state(frame):
            # These are planning metadata, not fabricated physical poses.
            return WorldState(vehicle_type='brick_crawler', vehicle_color=color,
                              environment='minimal_gray_track', track_style='light_gray',
                              time=frame/config.fps, progress=frame/(config.duration*config.fps),
                              camera_style=config.camera_style)
        total = config.duration*config.fps
        segments = []
        for index,start in enumerate(range(0,total,config.segment_seconds*config.fps),1):
            count = min(total-start,config.segment_seconds*config.fps)
            segments.append(SegmentPlan(index=index,seed=seed,start_frame=start,frame_count=count,
                                        start_state=state(start),end_state=state(start+count),
                                        sections=sections,checkpoints=[]))
        audio = self.audio(config)
        return Scenario(schema_version=2,theme='minimal_gray_track',duration=config.duration,aspect_ratio=config.aspect_ratio,
                        fps=config.fps,seed=seed,quality=config.quality,vehicle={'type':'brick_crawler','color':color},
                        environment={'lighting':'studio_soft'}, camera={'mode':config.camera_style},audio=audio,
                        speed=2.2,sections=sections,events=[],segments=segments,physics=True,
                        content_type='obstacle_course',idea=idea)

    def audio(self, config):
        audio = {'music':config.music,'sound_effects':config.sound_effects,'engine_sound':config.engine_sound}
        if config.sound:
            audio = {'music':config.sound in ('sfx_and_music','music_only'),
                     'sound_effects':config.sound in ('sfx_only','sfx_and_music'),
                     'engine_sound':config.sound in ('sfx_only','sfx_and_music')}
        return audio

    def track(self, duration, difficulty, seed):
        rng = random.Random(seed)
        sections = []
        cursor = 6.0
        order = ('platform_drop','ramp','stairs','gap')
        for i in range(max(1,int(duration*2.2/10))):
            kind = order[i%len(order)]
            height = (.55 if kind == 'platform_drop' else rng.uniform(.22,.38)) * difficulty/2
            sections.append(TrackSection(type=kind,start=cursor,length=6,width=5,
                                         gap=.5 if kind=='gap' else 0,difficulty=min(3,1+i//4),
                                         parameters={'height':height,'color':'track','seed':seed,'level':difficulty}))
            cursor += rng.uniform(9,10)
        return sections
