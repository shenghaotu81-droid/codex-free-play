import json
import subprocess
import numpy as np
import cv2

POLYGONS = [
 [[0,0],[30,0],[30,8],[8,8],[8,30],[0,30]],
 [[80,80],[50,80],[50,72],[72,72],[72,50],[80,50]],
 [[0,80],[30,80],[30,72],[8,72],[8,50],[0,50]],
 [[66,0],[80,0],[80,14],[72,14],[72,8],[66,8]],
 [[50,0],[58,0],[58,8],[50,8]], [[72,22],[80,22],[80,30],[72,30]]]
MODEL=np.array([[0,0,0],[.08,0,0],[.08,.08,0],[0,.08,0]],np.float64)

def matrix(camera):
    return np.array([[camera['focal_px'],0,camera['width']/2],[0,camera['focal_px'],camera['height']/2],[0,0,1.]],np.float64)

def mount_rotation(camera):
    """Camera axes into chassis-aligned camera axes (right/down/forward)."""
    rx,_=cv2.Rodrigues(np.array([camera['pitch_rad'],0.,0.]))
    ry,_=cv2.Rodrigues(np.array([0.,camera['yaw_rad'],0.]))
    rz,_=cv2.Rodrigues(np.array([0.,0.,camera['roll_rad']]))
    return rz@ry@rx

class BaselineVision:
    """Simple bbox + planar PnP + exponential velocity; deliberately a replaceable baseline."""
    def __init__(self, camera):
        self.camera=camera; self.previous=None; self.velocity=np.zeros(3)
    def process(self, image, frame_id, timestamp):
        mask=cv2.inRange(image,(180,180,180),(255,255,255))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        contours=[c for c in contours if cv2.contourArea(c)>5]
        if len(contours)<4: return None
        x,y,w,h=cv2.boundingRect(np.concatenate(contours))
        if w<10 or h<10: return None
        points=np.array([[x,y],[x+w-1,y],[x+w-1,y+h-1],[x,y+h-1]],np.float64)
        ok,r,t=cv2.solvePnP(MODEL,points,matrix(self.camera),np.array(self.camera['distortion'],float),flags=cv2.SOLVEPNP_IPPE)
        if not ok: return None
        R,_=cv2.Rodrigues(r); center=(R@np.array([.04,.04,0])+t.ravel())
        pos=center
        if self.previous and timestamp>self.previous[0]:
            measured=(pos-self.previous[1])/(timestamp-self.previous[0])
            self.velocity=.7*self.velocity+.3*measured
        self.previous=(timestamp,pos)
        return dict(x=float(pos[0]), y=float(pos[1]), depth=float(pos[2]), vx=float(self.velocity[0]), vy=float(self.velocity[1]), vz=float(self.velocity[2]), measured=True,measurement_at=timestamp)
    def close(self): pass

class CampusVision:
    """Persistent process: raw BGR in; actual pinned Detector/Pose/Tracker out. No truth input."""
    def __init__(self,camera,binary,config):
        self.process_handle=subprocess.Popen([str(binary),str(config),str(camera['width']),str(camera['height']),str(camera['focal_px']),*map(str,camera['distortion'])],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    def process(self,image,frame_id,timestamp):
        p=self.process_handle
        p.stdin.write(f'{frame_id} {round(timestamp*1e6)}\n'.encode()+image.tobytes()); p.stdin.flush()
        line=p.stdout.readline()
        if not line: raise RuntimeError('campus bridge exited; see stderr')
        result=json.loads(line)
        return result if result.get('available') else None
    def close(self):
        p=self.process_handle
        if p.stdin: p.stdin.close()
        try: p.wait(timeout=3)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
        if p.stdout: p.stdout.close()
