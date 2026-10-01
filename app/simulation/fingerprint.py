"""Invalidate physics caches when scene inputs, implementation or Blender change."""
import hashlib
import json
import subprocess
from pathlib import Path


def physics_fingerprint(scenario, binary, experiment_id=None):
    root = Path(__file__).parent
    digest = hashlib.sha256()
    inputs = {name:getattr(scenario,name) for name in ('duration','fps','seed','speed','vehicle','environment','camera')}
    inputs['sections'] = [section.model_dump() for section in scenario.sections]
    if experiment_id is not None:
        trial = next(trial for trial in scenario.experiments if trial.id==experiment_id)
        inputs['experiment'] = trial.model_dump(exclude={'refinement_reason'})
        inputs['content_type'] = scenario.content_type
    digest.update(json.dumps(inputs,sort_keys=True).encode())
    files = [root/name for name in ('physics_scene.py','physics_vehicle.py','physics_prototype.py','geometry.py','camera.py')]
    files.extend(sorted((root/'obstacles').glob('*.py')))
    if experiment_id is not None:
        files.append(root/'experiment_scene.py')
        files.extend(sorted((root/'worlds').glob('*.py')))
    for path in files:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    version = subprocess.run([str(binary),'--version'],capture_output=True,check=True,timeout=30).stdout
    digest.update(version)
    return digest.hexdigest()


def render_fingerprint(physics, scenario, segment, width, height, engine):
    inputs = {'physics':physics,'quality':scenario.quality,'aspect_ratio':scenario.aspect_ratio,
              'width':width,'height':height,'engine':engine,
              'start_frame':segment.start_frame,'frame_count':segment.frame_count,
              'show_labels':scenario.show_labels}
    return hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
