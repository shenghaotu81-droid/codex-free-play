"""Plugins receive a SensorPacket (no target truth/seed/future motion), return Command."""
from dataclasses import dataclass
import math
import bisect
import numpy as np
from .vision import mount_rotation

@dataclass(frozen=True)
class SensorPacket:
    time: float
    observation: dict | None
    velocity_world: tuple
    arm_state: str
    inventory: tuple
    enabled: bool
    heading_rad: float = 0
    image: object = None
    image_captured_at: float | None = None
    frame_id: int | None = None
    wire_feedback: tuple = ()

@dataclass(frozen=True)
class Command:
    vx: float=0
    vy: float=0
    wz: float=0
    release: bool=False
    speed_frame: bytes | None=None

class FollowPolicy:
    def __init__(self, settings):
        self.cfg=settings; self.stable=0; self.mount=mount_rotation(settings['camera'])
        self.odo=np.zeros(2); self.last_time=0.; self.history_times=[]; self.history_positions=[]
        self.previous_target=None; self.target_velocity=np.zeros(2)
    def step(self,s):
        c=self.cfg; obs=s.observation
        # Integrate ideal wheel-odometry feedback, then match it to capture time.
        # Adding today's chassis velocity to an old camera derivative creates feedback oscillation.
        self.odo+=np.array(s.velocity_world[:2])*(s.time-self.last_time); self.last_time=s.time
        self.history_times.append(s.time); self.history_positions.append(self.odo.copy())
        if not s.enabled or obs is None or s.time-obs.get('measurement_at',obs['captured_at'])>c['algorithm']['lost_timeout_s']:
            self.stable=0; return Command()
        a=c['algorithm']; arm=c['arm']
        age=s.time-obs['captured_at']
        position=self.mount@np.array([obs['x'],obs.get('y',0),obs['depth']])
        right=np.array([math.cos(s.heading_rad),math.sin(s.heading_rad)])
        forward=np.array([-math.sin(s.heading_rad),math.cos(s.heading_rad)])
        index=max(0,bisect.bisect_right(self.history_times,obs['captured_at']+1e-9)-1)
        at_capture=self.history_positions[index]
        target=at_capture+right*(position[0]+c['camera']['offset_x_m'])+forward*(position[2]+c['camera']['offset_y_m'])
        if self.previous_target is not None and obs['captured_at']>self.previous_target[0]:
            derivative=(target-self.previous_target[1])/(obs['captured_at']-self.previous_target[0])
            self.target_velocity=.65*self.target_velocity+.35*derivative
        self.previous_target=(obs['captured_at'],target)
        emitter=self.odo+right*arm['emitter_x_m']+forward*arm['emitter_forward_m']
        error=target+self.target_velocity*age-emitter
        relative=self.target_velocity-np.array(s.velocity_world[:2])
        desired=a['kp']*error
        if a['feedforward']: desired+=self.target_velocity
        horizon=c['link']['latency_s']+arm['release_delay_s']+math.sqrt(2*arm['drop_height_m']/9.81)
        impact_error=error+relative*horizon if a['predict_release'] else error
        margin=c['target']['opening_width_m']/2-arm['ore_radius_m']-a['release_margin_m']
        ready=(abs(impact_error[0])<margin and abs(impact_error[1])<c['target']['opening_depth_m']/2-arm['ore_radius_m'] and obs.get('measured',False))
        self.stable=self.stable+1 if ready else 0
        return Command(vx=float(desired@forward),vy=float(-desired@right),release=s.arm_state=='READY' and self.stable>=a['stable_frames'])

def make_policy(settings):
    return FollowPolicy(settings)
