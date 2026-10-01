import asyncio
import json
import logging
import shutil
import time
import math
from datetime import datetime
from pathlib import Path
from app.config import settings
from app.core.state_manager import ProjectStateManager
from app.engines.composer import VideoComposer
from app.models.project import ProjectConfig, PipelineStage, VideoType
from app.simulation.models import Scenario, SegmentProgress
from app.simulation.scenario import ScenarioGenerator
from app.simulation.blender_renderer import BlenderRenderer
from app.simulation.audio import SimulationAudioManager
from app.simulation.media import validate_media
from app.simulation.lock import ProjectLease

logger = logging.getLogger(__name__)


def prepare_simulation_project(project_id, config):
    manager = ProjectStateManager(project_id)
    state = manager.init_project_structure(ProjectConfig(
        project_id=project_id, topic='Colorful toy vehicle obstacle course',
        video_type=VideoType.SIMULATION_VIDEO, simulation=config,
        platform='youtube' if config.aspect_ratio=='16:9' else 'tiktok', target_duration=config.duration))
    return manager, state


class SimulationVideoService:
    def __init__(self, renderer=None):
        self.renderer = renderer or BlenderRenderer()

    async def generate_video(self, project_id, config):
        with ProjectLease(ProjectStateManager(project_id).project_dir):
            return await self._generate(project_id, config)

    async def _generate(self, project_id, config):
        manager, state = prepare_simulation_project(project_id, config)
        root = manager.project_dir
        config = state.config.simulation
        if config is None:
            raise ValueError('Project is not a simulation video')
        log_path = root / 'logs' / 'simulation.jsonl'

        def record(event, **data):
            entry = {'time': datetime.now().isoformat(), 'video_id': project_id, 'event': event, **data}
            with log_path.open('a', encoding='utf-8') as log:
                log.write(json.dumps(entry) + '\n')
            logger.info('%s', entry)

        def save(stage, progress, message):
            state.stage, state.progress_percentage, state.progress_message = stage, progress, message
            state.updated_at = datetime.now()
            manager.save_state(state)

        try:
            save(PipelineStage.SIMULATION_PLANNING, 5, 'Planning simulation')
            scenario_path = root / 'scenario.json'
            if scenario_path.exists():
                scenario = Scenario.model_validate_json(scenario_path.read_text(encoding='utf-8'))
                if scenario.schema_version < 2:
                    raise RuntimeError('Legacy animated scenario cannot resume as physics. Create a new physics project.')
            else:
                scenario = ScenarioGenerator().generate(config)
                temporary = root / 'scenario.json.tmp'
                temporary.write_text(scenario.model_dump_json(indent=2), encoding='utf-8')
                temporary.replace(scenario_path)
            config.seed = scenario.seed
            state.config.simulation = config
            state.config.topic = scenario.idea.get('title',state.config.topic)
            record('scenario', seed=scenario.seed, duration=scenario.duration, obstacles=[s.type for s in scenario.sections])
            save(PipelineStage.SIMULATION_TRACK, 10, 'Track validated; preparing segments')
            self.renderer.check_available()
            width, height = config.dimensions()
            for segment in scenario.segments:
                if segment.index not in state.segments_progress:
                    state.segments_progress[segment.index] = SegmentProgress(segment_id=segment.index, seed=segment.seed,
                                                                            duration=segment.frame_count/scenario.fps)
            manager.save_state(state)
            outputs = []
            for segment in scenario.segments:
                progress = state.segments_progress[segment.index]
                directory = root / 'segments' / f'{segment.index:03d}'
                output = directory / 'output.mp4'
                fingerprint = self.renderer.render_fingerprint(scenario,segment,width,height)
                cached = False
                if progress.status == 'COMPLETED' and output.exists():
                    try:
                        if isinstance(fingerprint,str):
                            timing = json.loads((directory/'timing.json').read_text(encoding='utf-8')) if (directory/'timing.json').exists() else {}
                            if timing.get('fingerprint')!=fingerprint:
                                raise RuntimeError('Cached segment physics fingerprint changed')
                        await validate_media(output,width,height,progress.duration,scenario.fps)
                        cached = True
                    except (RuntimeError,ValueError,OSError) as error:
                        record('cache_invalid', segment_id=segment.index, error=str(error))
                if not cached:
                    for retry in range(settings.BLENDER_SEGMENT_RETRIES+1):
                        progress.status, progress.error = 'RENDERING', None
                        progress.attempts += 1
                        progress.checkpoint = {'segment':segment.index, 'seed':segment.seed,
                                               'vehicle_state':segment.start_state.model_dump(), 'frame':segment.start_frame,
                                               'render_status':'RENDERING'}
                        save(PipelineStage.SIMULATION_RENDERING,10+80*(segment.index-1)/len(scenario.segments),
                             f'Rendering {segment.index}/{len(scenario.segments)} (attempt {progress.attempts})')
                        record('render_start',segment_id=segment.index,seed=segment.seed,retry_count=progress.attempts-1,
                               duration=progress.duration,obstacles=[s.type for s in segment.sections])
                        started = time.monotonic()
                        try:
                            output = await self.renderer.render_segment(scenario,segment,directory,width,height)
                            telemetry_path = directory/'telemetry.json'
                            if telemetry_path.exists():
                                telemetry = json.loads(telemetry_path.read_text(encoding='utf-8'))
                                samples = telemetry['samples']
                                offset = segment.start_frame-telemetry.get('sample_start_frame',0)
                                bodies = samples[offset+segment.frame_count-1]
                                for world_state,frame_bodies in ((segment.start_state,samples[offset]),(segment.end_state,bodies)):
                                    end = frame_bodies[0]
                                    world_state.position = tuple(end['position'])
                                    world_state.rotation = tuple(end['rotation'])
                                    w,x,y,z = end['rotation']
                                    world_state.pitch = math.asin(max(-1,min(1,2*(w*y-z*x))))
                                    world_state.physical_bodies = frame_bodies
                                progress.checkpoint['physical_bodies'] = bodies
                                # Authoritative trajectory events replace prior retry/resume events.
                                if segment.experiment_id is None:
                                    scenario.events = telemetry['events']
                                    if 'result' in telemetry:
                                        scenario.results = [telemetry['result']]
                                else:
                                    scenario.events = [e for e in scenario.events if e.get('experiment_id')!=segment.experiment_id]+telemetry['events']
                                    result = telemetry['result']
                                    scenario.results = [r for r in scenario.results if r['experiment_id']!=segment.experiment_id]+[result]
                                    scenario.results.sort(key=lambda r:r['experiment_id'])
                                    current = next(trial for trial in scenario.experiments if trial.id==segment.experiment_id)
                                    following = next((trial for trial in scenario.experiments if trial.id==current.id+1),None)
                                    if following:
                                        from app.simulation.experiments import refine_next_trial
                                        refine_next_trial(current,following,result)
                            progress.status, progress.output_path = 'COMPLETED', str(output)
                            progress.checkpoint = {'segment':segment.index, 'seed':segment.seed, 'frame':segment.start_frame+segment.frame_count,
                             'vehicle_state':segment.end_state.model_dump(), 'render_status':'COMPLETED',
                             'physical_bodies':progress.checkpoint.get('physical_bodies',[])}
                            record('render_complete',segment_id=segment.index,render_seconds=time.monotonic()-started)
                            temporary = root/'scenario.json.tmp'
                            temporary.write_text(scenario.model_dump_json(indent=2),encoding='utf-8')
                            temporary.replace(scenario_path)
                            manager.save_state(state)
                            break
                        except Exception as error:
                            progress.status, progress.error = 'FAILED', str(error)
                            progress.checkpoint['render_status'] = 'FAILED'
                            record('render_failed',segment_id=segment.index,error=str(error),retry_count=progress.attempts-1)
                            manager.save_state(state)
                            if retry == settings.BLENDER_SEGMENT_RETRIES:
                                raise
                outputs.append(str(output))
                save(PipelineStage.SIMULATION_RENDERING,10+80*segment.index/len(scenario.segments),
                     f'Rendered {segment.index}/{len(scenario.segments)}')
            save(PipelineStage.AUDIO_MIXING,92,'Synthesizing simulation sound effects and music')
            audio_path = root/'audio'/'simulation.wav'
            await SimulationAudioManager().generate_async(scenario,audio_path)
            save(PipelineStage.COMPOSITING,95,'Composing simulation segments')
            final = root/'final'/'video.mp4'
            started = time.monotonic()
            await VideoComposer().compose_simulation(outputs,str(audio_path),str(final),scenario.duration)
            record('compose_complete',ffmpeg_seconds=time.monotonic()-started)
            save(PipelineStage.QC,98,'Checking complete MP4')
            qc = await validate_media(final,width,height,scenario.duration,scenario.fps,require_audio=True)
            exported = settings.OUTPUTS_DIR / project_id
            exported.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(final,exported/'final.mp4')
            shutil.copyfile(scenario_path,exported/'scenario.json')
            preview = root/'segments'/'001'/'preview.png'
            if preview.exists():
                shutil.copyfile(preview,exported/'thumbnail.png')
            metadata = {'video_type':'physics_simulation_video','youtube_title':scenario.idea.get('title','Construction Brick Physics Obstacle Course'),
                         'tiktok_caption':scenario.idea.get('description','Brick crawler physics'), 'seed':scenario.seed,
                         'duration':scenario.duration,'segments':len(scenario.segments),'qc_result':qc,
                         'content_type':scenario.content_type,'idea':scenario.idea,'experiment_results':scenario.results}
            if scenario.experiments:
                from app.simulation.experiments import summarize_results
                metadata['comparison_summary'] = summarize_results(scenario.results)
                (exported/'experiment_results.json').write_text(json.dumps(scenario.results,indent=2),encoding='utf-8')
            (exported/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
            state.master_video_path = str(final)
            if config.aspect_ratio=='16:9':
                state.youtube_video_path = str(exported/'final.mp4')
            else:
                state.tiktok_video_path = str(exported/'final.mp4')
            state.metadata_path = str(exported/'metadata.json')
            if settings.BLENDER_CLEANUP:
                for segment in scenario.segments:
                    directory = root/'segments'/f'{segment.index:03d}'
                    for working_dir in [directory,*list((directory/'attempts').glob('*'))]:
                        for temporary in [*list((working_dir/'frames').glob('*.png')),*list(working_dir.glob('*.blend*'))]:
                            try:
                                temporary.unlink()
                            except OSError as error:
                                record('cleanup_deferred',segment_id=segment.index,path=str(temporary),error=str(error))
            save(PipelineStage.COMPLETED,100,'Simulation video ready')
            record('completed',seed=scenario.seed,duration=scenario.duration)
            return {'project_id':project_id,'final_video_path':str(exported/'final.mp4'),
                    'master_video_path':str(final),'duration':scenario.duration,'segments_count':len(scenario.segments),
                    'seed':scenario.seed,'qc_result':qc,'metadata':metadata}
        except (Exception, asyncio.CancelledError) as error:
            message = str(error) or 'Generation cancelled; resume to retry unfinished segments'
            for progress in state.segments_progress.values():
                if progress.status=='RENDERING':
                    progress.status, progress.error = 'FAILED', message
            state.errors.append(message)
            save(PipelineStage.FAILED,state.progress_percentage,message)
            record('failed',error=message)
            raise
