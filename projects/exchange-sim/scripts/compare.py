"""Paired experiments: same seed/scene, two replaceable policies, saved evidence."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
import cv2

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from exchange_sim.world import load_config
from exchange_sim.runtime import make_world,save_run,fresh_run,local_output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path)
    p.add_argument('--seeds',type=int,nargs='+',default=[7,11,23])
    p.add_argument('--modes',nargs='+',choices=['fixed','intermittent','uniform','random'],default=['fixed','random'])
    p.add_argument('--vision',default='auto')
    p.add_argument('--policy-a',help='module[:factory]; default predictive baseline')
    p.add_argument('--policy-b',help='module[:factory]; default reactive baseline')
    p.add_argument('--duration',type=float)
    p.add_argument('--output',type=Path)
    a=p.parse_args();cv2.setNumThreads(1)
    root=local_output(a.output or fresh_run());root.mkdir(parents=True,exist_ok=False)
    rows=[]
    base=load_config(a.config)
    for mode in a.modes:
        for seed in a.seeds:
            scenario=copy.deepcopy(base);scenario['target']['mode']=mode;scenario['seed']=seed
            if a.duration is not None:scenario['duration_s']=a.duration
            scene_only={k:v for k,v in scenario.items() if k!='algorithm'}
            fingerprint=hashlib.sha256(json.dumps(scene_only,sort_keys=True).encode()).hexdigest()
            for name,policy in [('A',a.policy_a),('B',a.policy_b)]:
                config=copy.deepcopy(scenario)
                if name=='B' and not policy:config['algorithm'].update(feedforward=False,predict_release=False)
                world=make_world(load_config(config),a.vision,policy)
                started=time.monotonic()
                try:
                    while world.step():pass
                    run=root/f'{mode}-{seed}-{name}';save_run(world,run)
                    row=dict(mode=mode,variant=name,scene_sha256=fingerprint,**world.summary(),**world.provenance)
                    row['wall_s']=round(time.monotonic()-started,3);rows.append(row)
                    (root/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
                    print(f"{mode} seed={seed} {name}: hits={world.hits} misses={world.misses} ({row['wall_s']:.1f}s)",flush=True)
                finally:world.close()
    lines=['# Paired simulation comparison','','Same scene hash means identical target motion and frame-indexed disturbances.','',
           '| Mode | Seed | Variant | Hits | Misses | Unreleased | Measured frames |','| --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        lines.append(f"| {row['mode']} | {row['seed']} | {row['variant']} | {row['hits']} | {row['misses']} | {row['remaining']+int(row['carrying'])} | {row['measured_frames']}/{row['frames']} |")
    lines+=['','A defaults to prediction + feedforward; B defaults to reactive position control.',
            'A custom policy replaces its corresponding default. Outcomes apply to this model and these seeds only.']
    (root/'comparison.md').write_text('\n'.join(lines)+'\n');print(root)


if __name__=='__main__':main()
