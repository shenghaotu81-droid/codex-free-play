"""Project-local runtime, plugin loading and provenance."""
import importlib
import json
import hashlib
import inspect
from pathlib import Path
from datetime import datetime
from .vision import BaselineVision, CampusVision
from .world import World

PROJECT = Path(__file__).resolve().parents[1]


def local_output(path):
    resolved=Path(path).resolve()
    if not resolved.is_relative_to(PROJECT):
        raise ValueError('output must stay within projects/exchange-sim')
    return resolved


def fresh_run():
    return PROJECT/'.local'/'runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')


def plugin(spec,default='make_policy'):
    module,_,name=spec.partition(':')
    return getattr(importlib.import_module(module),name or default)


class NoVision:
    def process(self,*args): return None
    def close(self): pass


def make_world(config,vision='auto',policy=None,campus_config=None):
    manifest=PROJECT/'.local'/'campus-bridge.json'
    requested=vision
    if vision=='auto': vision='campus' if manifest.exists() else 'baseline'
    provenance={'vision':vision,'requested_vision':requested,'policy':policy or 'exchange_sim.policies:make_policy'}
    if vision=='campus':
        if not manifest.exists():
            raise ValueError('build the campus bridge first: python3 scripts/build_campus_bridge.py')
        m=json.loads(manifest.read_text())
        perception=CampusVision(config['camera'],m['binary'],campus_config or m['config'])
        provenance['campus_revision']=m['revision']
        provenance['campus_config']=str(campus_config or m['config'])
        provenance['campus_binary_sha256']=hashlib.sha256(Path(m['binary']).read_bytes()).hexdigest()
        config_digest=hashlib.sha256()
        for source in sorted(Path(campus_config or m['config']).glob('*.yaml')):
            config_digest.update(source.name.encode());config_digest.update(source.read_bytes())
        provenance['campus_config_sha256']=config_digest.hexdigest()
    elif vision=='baseline': perception=BaselineVision(config['camera'])
    elif vision=='none': perception=NoVision()
    else:
        perception=plugin(vision,'make_vision')(config['camera'])
    try:
        world=World(config,vision=perception,policy_factory=plugin(policy) if policy else None)
    except Exception:
        perception.close()
        raise
    digest=hashlib.sha256()
    for source in sorted((PROJECT/'exchange_sim').glob('*.py'))+[PROJECT/'native/bridge.cpp']:
        digest.update(source.relative_to(PROJECT).as_posix().encode()); digest.update(source.read_bytes())
    provenance['simulator_sha256']=digest.hexdigest()
    for name,obj in [('policy',world.policy),('vision',world.vision)]:
        source=inspect.getsourcefile(type(obj))
        if source:provenance[name+'_entry_sha256']=hashlib.sha256(Path(source).read_bytes()).hexdigest()
    world.provenance=provenance
    return world


def save_run(world,path=None,label=None):
    from .render import dashboard
    directory=local_output(path or fresh_run())
    world.save(directory)
    (directory/'provenance.json').write_text(json.dumps(world.provenance,indent=2)+'\n')
    dashboard(world,label or world.provenance['vision']).save(directory/'snapshot.png')
    return directory
