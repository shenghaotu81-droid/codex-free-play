"""Native CPU simulator and repeatable headless experiments."""
import argparse
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np
from .world import load_config
from .runtime import make_world,save_run,local_output,fresh_run


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless',action='store_true',help='run to the deadline without a display')
    parser.add_argument('--config',type=Path,help='JSON overrides; see configs/exchange.json')
    parser.add_argument('--vision',default='auto',help='auto / campus / baseline / none / module:make_vision')
    parser.add_argument('--campus-config',type=Path,help='alternate local YAML directory for the C++ chain')
    parser.add_argument('--policy',help='Python module[:make_policy], consumes SensorPacket including raw BGR')
    parser.add_argument('--variant',choices=['predictive','reactive'],default='predictive')
    parser.add_argument('--mode',choices=['fixed','intermittent','uniform','random'])
    parser.add_argument('--seed',type=int)
    parser.add_argument('--duration',type=float,help='override 60s for a shorter experiment')
    parser.add_argument('--output',type=Path,help='new run directory inside this project')
    parser.add_argument('--video',action='store_true',help='write a CPU-rendered 15fps MJPEG demo.avi')
    args=parser.parse_args(argv)
    cv2.setNumThreads(1)
    try:
        config=load_config(args.config)
        if args.mode: config['target']['mode']=args.mode
        if args.seed is not None: config['seed']=args.seed
        if args.duration is not None: config['duration_s']=args.duration
        if args.variant=='reactive':
            config['algorithm'].update(feedforward=False,predict_release=False)
        config=load_config(config)
        if args.output:
            output=local_output(args.output)
            if output.exists(): raise FileExistsError(f'output already exists: {output}')
        if not args.headless:
            from .desktop import launch
            launch(config,args)
            return 0
        world=make_world(config,args.vision,args.policy,args.campus_config)
        writer=None; staging=None
        started=time.monotonic()
        try:
            if args.video:
                from .render import dashboard
                # Stage the video under .local; save_run reserves the final directory.
                staging=fresh_run().parent.parent/'tmp'/(fresh_run().name+'.avi'); staging.parent.mkdir(parents=True,exist_ok=True)
                writer=cv2.VideoWriter(str(staging),cv2.VideoWriter_fourcc(*'MJPG'),15,(1360,900))
                if not writer.isOpened(): raise RuntimeError('MJPEG encoder is unavailable')
                next_video=1/15
            while world.step():
                if writer:
                    while world.time+1e-9>=next_video:
                        writer.write(np.asarray(dashboard(world,world.provenance['vision']))[:,:,::-1])
                        next_video+=1/15
            if writer: writer.release(); writer=None
            output=save_run(world,args.output)
            if staging: staging.rename(output/'demo.avi')
            print(json.dumps(dict(world.summary(),output=str(output),cpu_run_wall_s=round(time.monotonic()-started,3),**world.provenance),indent=2))
        finally:
            if writer: writer.release()
            world.close()
            if staging and staging.exists(): staging.unlink()
        return 0
    except (ValueError,TypeError,KeyError,OSError,RuntimeError,ImportError) as exc:
        print(f'exchange-sim: {exc}',file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__=='__main__':
    raise SystemExit(main())
