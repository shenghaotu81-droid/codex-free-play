"""Deterministic CPU world. Truth stays here and is never passed to a policy."""
import copy
import csv
import hashlib
import importlib
import json
import math
from pathlib import Path
import numpy as np
import cv2
from .vision import POLYGONS, matrix, mount_rotation, BaselineVision
from .policies import SensorPacket
from .protocol import encode_speed, decode_speed, encode_velocity_feedback

DEFAULT=Path(__file__).resolve().parents[1]/'configs/exchange.json'

def load_config(path=None):
    c=json.loads(DEFAULT.read_text())
    def merge(dst,src):
        for k,v in src.items():
            if k not in dst: raise ValueError(f'unknown parameter: {k}')
            if isinstance(dst[k],dict):
                if not isinstance(v,dict): raise ValueError(f'{k} must be an object')
                merge(dst[k],v)
            else: dst[k]=v
    if path:
        overrides=path if isinstance(path,dict) else json.loads(Path(path).read_text())
        if not isinstance(overrides,dict): raise ValueError('configuration must be an object')
        merge(c,overrides)
    def finite(v):
        if isinstance(v,dict):
            for x in v.values(): finite(x)
        elif isinstance(v,list):
            for x in v: finite(x)
        elif isinstance(v,(float,int)) and not math.isfinite(v): raise ValueError('parameters must be finite')
    finite(c)
    if not isinstance(c['seed'],int) or c['seed']<0: raise ValueError('seed must be a non-negative integer')
    if not 0<c['dt_s']<=.1 or not 0<c['duration_s']<=600 or not 0<c['physics_dt_s']<=min(.01,c['dt_s']): raise ValueError('invalid time range')
    cam=c['camera']; arm=c['arm']; ch=c['chassis']; target=c['target']
    if target['mode'] not in ('fixed','intermittent','uniform','random'): raise ValueError('invalid target mode')
    for key in ('width','height'):
        if not isinstance(cam[key],int) or not 64<=cam[key]<=4096: raise ValueError('invalid image size')
    if len(cam['distortion'])!=5 or cam['focal_px']<=0: raise ValueError('invalid camera')
    if not 0<=cam['brightness']<=255: raise ValueError('brightness must be 0..255')
    if cam['blur_px']<1 or int(cam['blur_px'])!=cam['blur_px'] or cam['blur_px']%2!=1: raise ValueError('blur_px must be positive odd integer')
    for group,key in ((cam,'dropout_probability'),(arm,'grasp_failure_probability'),(c['link'],'loss_probability')):
        if not 0<=group[key]<=1: raise ValueError('probabilities must be 0..1')
    if not arm['inventory'] or len(arm['inventory'])!=len(arm['storage_xy_m']) or any(not isinstance(n,int) or n<0 for n in arm['inventory']): raise ValueError('invalid inventory')
    if any(not isinstance(point,list) or len(point)!=2 for point in arm['storage_xy_m']): raise ValueError('storage_xy_m must contain [right, forward] pairs')
    for section,keys in ((cam,('height_m','noise_sigma','latency_s','occlusion_period_s','occlusion_duration_s')),(arm,('pick_s','lift_s','return_s','release_delay_s','drop_height_m','ore_radius_m','scatter_sigma_m')),(c['link'],('latency_s','watchdog_s')),(target,('speed_mps','half_travel_m','opening_width_m','opening_depth_m')),(ch,('max_speed_mps','max_yaw_rate','max_yaw_accel','max_accel_mps2','response_s','slip_scale'))):
        if any(section[k]<0 for k in keys): raise ValueError('negative physical parameter')
    if ch['response_s']<=0 or c['link']['watchdog_s']<=0: raise ValueError('response/watchdog must be positive')
    if not isinstance(c['algorithm']['stable_frames'],int) or c['algorithm']['stable_frames']<1 or c['algorithm']['lost_timeout_s']<0 or c['algorithm']['kp']<0 or c['algorithm']['release_margin_m']<0: raise ValueError('invalid algorithm settings')
    for key in ('feedforward','predict_release'):
        if not isinstance(c['algorithm'][key],bool): raise ValueError(f'{key} must be boolean')
    return c

class World:
    def __init__(self,c,vision=None,policy_factory=None):
        self.c=copy.deepcopy(c); self.time=0.; self.frame=0
        self.car=np.array([c['chassis']['initial_x_m'],c['chassis']['initial_y_m'],c['chassis']['initial_yaw_rad']],float)
        self.vel=np.zeros(3); self.command=np.zeros(3); self.last_rx=-1.
        self.inventory=list(c['arm']['inventory']); self.slot=0; self.arm_state='PICK'; self.arm_until=c['arm']['pick_s']
        self.carry=False; self.picks=0; self.sensor_queue=[]; self.command_queue=[]; self.observation=None
        self.flying=[]; self.landed=[]; self.log=[]; self.events=[]; self.hits=0; self.misses=0; self.grasp_failures=0; self.watchdogs=0
        self.vision=vision or BaselineVision(c['camera']); self.sensor_image=None; self.sensor_stamp=None; self.sensor_frame=None
        self.measured_frames=0; self.available_frames=0; self.rejected_frames=0
        # Policy gets only deployable settings. No seed or target future-motion parameters.
        settings={k:copy.deepcopy(c[k]) for k in ('camera','arm','algorithm')}
        settings['link']={'latency_s':c['link']['latency_s']}
        settings['target']={k:c['target'][k] for k in ('opening_width_m','opening_depth_m')}
        factory=policy_factory or importlib.import_module('exchange_sim.policies').make_policy
        self.policy=factory(settings)
        self.targets=self._trajectory(); self.image=np.zeros((c['camera']['height'],c['camera']['width'],3),np.uint8)
    def _trajectory(self):
        c=self.c; t=c['target']; rng=np.random.default_rng(c['seed']); x=0.; direction=1; endpoint=t['half_travel_m']; result=[]
        for i in range(math.ceil(c['duration_s']/c['physics_dt_s'])+1000):
            now=i*c['physics_dt_s']; active=t['mode']!='fixed' and (t['mode']!='intermittent' or now%30<10)
            velocity=direction*t['speed_mps'] if active else 0
            result.append((x,velocity))
            x+=velocity*c['physics_dt_s']
            if direction*(x-endpoint)>=0:
                x=endpoint; direction*=-1
                endpoint=(rng.uniform(-t['half_travel_m'],x-.06) if direction<0 and x> -t['half_travel_m']+.06 else -t['half_travel_m']) if t['mode']=='random' else direction*t['half_travel_m']
                if t['mode']=='random' and direction>0:
                    endpoint=rng.uniform(min(t['half_travel_m'],x+.06),t['half_travel_m'])
        return result
    def target_at(self,time):
        index=min(len(self.targets)-1,max(0,int(time/self.c['physics_dt_s'])))
        x,_=self.targets[index]
        following=self.targets[min(index+1,len(self.targets)-1)][0]
        fraction=min(1.,max(0.,time/self.c['physics_dt_s']-index))
        return x+(following-x)*fraction
    def render_camera(self):
        c=self.c; cam=c['camera']; rng=np.random.default_rng(np.random.SeedSequence([c['seed'],self.frame,1]))
        image=np.full((cam['height'],cam['width'],3),24,np.uint8)
        angle=self.car[2]
        dx=self.target_at(self.time)-self.car[0]-cam['offset_x_m']*math.cos(angle)+cam['offset_y_m']*math.sin(angle)
        dy=-self.car[1]-cam['offset_x_m']*math.sin(angle)-cam['offset_y_m']*math.cos(angle)
        x=dx*math.cos(angle)+dy*math.sin(angle); depth=-dx*math.sin(angle)+dy*math.cos(angle)
        R,_=cv2.Rodrigues(np.array([0.,angle,0.])); mount=mount_rotation(cam)
        R=mount.T@R; r,_=cv2.Rodrigues(R)
        center=mount.T@np.array([x,cam['height_m']-c['target']['marker_top_m']+.04,depth]); t=center-R@np.array([.04,.04,0])
        hidden=(cam['occlusion_period_s']>0 and self.time%cam['occlusion_period_s']<cam['occlusion_duration_s']) or rng.random()<cam['dropout_probability']
        if center[2]>.08 and not hidden:
            for polygon in POLYGONS:
                points=np.array([[a*.001,b*.001,0] for a,b in polygon],float)
                pixels,_=cv2.projectPoints(points,r,t,matrix(cam),np.array(cam['distortion'],float))
                cv2.fillPoly(image,[np.clip(pixels.reshape(-1,2),-10000,10000).astype(np.int32)],(cam['brightness'],)*3)
        if cam['blur_px']>1: image=cv2.GaussianBlur(image,(cam['blur_px'],)*2,0)
        if cam['noise_sigma']>0: image=np.clip(image.astype(float)+rng.normal(0,cam['noise_sigma'],image.shape[:2])[...,None],0,255).astype(np.uint8)
        return image
    def _event(self,name,at=None,**kwargs): self.events.append(dict(time=round(self.time if at is None else at,6),event=name,**kwargs))
    def _arm(self):
        a=self.c['arm']
        if self.time+1e-9<self.arm_until: return
        if self.arm_state=='PICK':
            if not any(self.inventory): self.arm_state='EMPTY'; self._event('inventory_empty'); return
            while self.inventory[self.slot]==0: self.slot=(self.slot+1)%len(self.inventory)
            rng=np.random.default_rng(np.random.SeedSequence([self.c['seed'],self.picks,2])); self.picks+=1
            if rng.random()<a['grasp_failure_probability']:
                self.grasp_failures+=1; self.arm_until=self.time+a['pick_s']; self._event('grasp_failed'); return
            self.inventory[self.slot]-=1; self.carry=True; self.arm_state='LIFT'; self.arm_until=self.time+a['lift_s']; self._event('grasped',slot=self.slot)
        elif self.arm_state=='LIFT': self.arm_state='READY'; self._event('at_release_pose')
        elif self.arm_state=='OPEN':
            angle=self.car[2]; forward=np.array([-math.sin(angle),math.cos(angle)]); right=np.array([math.cos(angle),math.sin(angle)])
            point=self.car[:2]+forward*a['emitter_forward_m']+right*a['emitter_x_m']
            duration=math.sqrt(2*a['drop_height_m']/9.81)
            rng=np.random.default_rng(np.random.SeedSequence([self.c['seed'],self.picks,3]))
            # A rotating chassis also gives the offset gripper tangential velocity.
            lever=forward*a['emitter_forward_m']+right*a['emitter_x_m']
            tip_velocity=self.vel[:2]*self.c['chassis']['slip_scale']+self.vel[2]*np.array([-lever[1],lever[0]])
            landing=point+tip_velocity*duration+rng.normal(0,a['scatter_sigma_m'],2)
            self.flying.append(dict(start=self.time,end=self.time+duration,point=point.tolist(),landing=landing.tolist()))
            self.carry=False; self.arm_state='RETURN'; self.arm_until=self.time+a['return_s']; self._event('released')
        elif self.arm_state=='RETURN':
            self.slot=(self.slot+1)%len(self.inventory); self.arm_state='PICK'; self.arm_until=self.time+a['pick_s']
    def step(self):
        if self.time>=self.c['duration_s']-1e-9: return False
        c=self.c; dt=min(c['dt_s'],c['duration_s']-self.time); self.image=self.render_camera()
        obs=self.vision.process(self.image,self.frame,self.time)
        if obs is not None: obs=dict(obs,captured_at=self.time)
        self.available_frames+=int(obs is not None)
        self.measured_frames+=int(obs is not None and obs.get('measured',False))
        self.image.setflags(write=False)
        self.sensor_queue.append((self.time+c['camera']['latency_s'],obs,self.image,self.frame,self.time))
        while self.sensor_queue and self.sensor_queue[0][0]<=self.time+1e-9:
            _,self.observation,self.sensor_image,self.sensor_frame,self.sensor_stamp=self.sensor_queue.pop(0)
        angle=self.car[2]
        body_forward=-math.sin(angle)*self.vel[0]+math.cos(angle)*self.vel[1]
        body_left=-math.cos(angle)*self.vel[0]-math.sin(angle)*self.vel[1]
        feedback=encode_velocity_feedback(body_forward,body_left,self.vel[2],self.frame)
        s=SensorPacket(self.time,copy.deepcopy(self.observation),tuple(self.vel),self.arm_state,tuple(self.inventory),True,float(self.car[2]),self.sensor_image,self.sensor_stamp,self.sensor_frame,(feedback,))
        cmd=self.policy.step(s)
        if not all(math.isfinite(v) for v in (cmd.vx,cmd.vy,cmd.wz)): raise ValueError('policy returned non-finite command')
        wire=cmd.speed_frame if cmd.speed_frame is not None else encode_speed(cmd.vx,cmd.vy,cmd.wz,True,self.frame,self.time)
        rng=np.random.default_rng(np.random.SeedSequence([c['seed'],self.frame,4]))
        if rng.random()>=c['link']['loss_probability']: self.command_queue.append((self.time+c['link']['latency_s'],wire,bool(cmd.release)))
        wire_sent=wire
        end=self.time+dt
        while self.time<end-1e-9:
            substep=min(c['physics_dt_s'],end-self.time)
            self._physics(substep)
            self.time+=substep
        self.time=end
        self.log.append(dict(time=self.time,target_x=self.target_at(self.time),car_x=float(self.car[0]),car_y=float(self.car[1]),estimate_x=None if self.observation is None else self.observation['x'],arm=self.arm_state,hits=self.hits,misses=self.misses,remaining=sum(self.inventory),command_vx=cmd.vx,command_vy=cmd.vy,velocity_world_x=float(self.vel[0]),measurement_age_s=None if self.observation is None else self.time-self.observation.get('measurement_at',self.observation['captured_at']),release_requested=bool(cmd.release),speed_frame_hex=wire_sent.hex()))
        self.frame+=1; self.time=min(c['duration_s'],self.frame*c['dt_s'])
        if self.time>=c['duration_s']-1e-9: self._event('deadline')
        return True

    def _physics(self,dt):
        c=self.c
        while self.command_queue and self.command_queue[0][0]<=self.time+1e-9:
            _,wire,release=self.command_queue.pop(0)
            try: decoded=decode_speed(wire)
            except ValueError:
                self.rejected_frames+=1; self._event('invalid_speed_frame'); continue
            self.command=np.array(decoded); self.last_rx=self.time
            if release and self.arm_state=='READY':
                self.arm_state='OPEN'; self.arm_until=self.time+c['arm']['release_delay_s']; self._event('release_requested')
        self._arm()
        expired=self.time-self.last_rx>c['link']['watchdog_s']
        if expired and np.any(self.command): self.watchdogs+=1; self.command[:]=0; self._event('watchdog_stop')
        ch=c['chassis']; vx,vy,wz=self.command; angle=self.car[2]
        desired=np.array([-math.sin(angle)*vx-math.cos(angle)*vy, math.cos(angle)*vx-math.sin(angle)*vy,wz])
        speed=np.linalg.norm(desired[:2]); desired[:2]*=min(1,ch['max_speed_mps']/max(speed,1e-9)); desired[2]=np.clip(desired[2],-ch['max_yaw_rate'],ch['max_yaw_rate'])
        change=(desired-self.vel)*min(1,dt/ch['response_s'])
        acceleration=np.linalg.norm(change[:2]); change[:2]*=min(1,ch['max_accel_mps2']*dt/max(acceleration,1e-12))
        change[2]=np.clip(change[2],-ch['max_yaw_accel']*dt,ch['max_yaw_accel']*dt)
        self.vel+=change
        self.car[:2]+=self.vel[:2]*dt*ch['slip_scale']; self.car[2]+=self.vel[2]*dt
        # Resolve impacts at their own scheduled time, never grant points from a command/ACK.
        for shot in self.flying[:]:
            if shot['end']<=self.time+dt+1e-9:
                point=shot['landing']; tx=self.target_at(shot['end']); r=c['arm']['ore_radius_m']
                hit=shot['end']<=c['duration_s'] and abs(point[0]-tx)+r<=c['target']['opening_width_m']/2 and abs(point[1])+r<=c['target']['opening_depth_m']/2
                self.hits+=int(hit); self.misses+=int(not hit); shot.update(hit=hit,target_x=tx); self.landed.append(shot); self.flying.remove(shot)
                self._event('hit' if hit else 'miss',at=shot['end'],landing=point,target_x=tx)
    def summary(self):
        return dict(hits=self.hits,misses=self.misses,pending_flights=len(self.flying),remaining=sum(self.inventory),carrying=self.carry,grasp_failures=self.grasp_failures,watchdog_stops=self.watchdogs,rejected_frames=self.rejected_frames,measured_frames=self.measured_frames,available_frames=self.available_frames,frames=self.frame,duration_s=self.time,seed=self.c['seed'],config_sha256=hashlib.sha256(json.dumps(self.c,sort_keys=True).encode()).hexdigest(),model='planar chassis + scripted arm + ballistic drop; not hardware certification')
    def save(self,directory):
        directory=Path(directory); directory.mkdir(parents=True,exist_ok=False)
        (directory/'config.json').write_text(json.dumps(self.c,indent=2))
        (directory/'summary.json').write_text(json.dumps(self.summary(),indent=2))
        (directory/'events.json').write_text(json.dumps(self.events,indent=2))
        if self.log:
            with (directory/'frames.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(self.log[0])); w.writeheader(); w.writerows(self.log)
    def close(self):
        self.vision.close()
        if hasattr(self.policy,'close'): self.policy.close()
