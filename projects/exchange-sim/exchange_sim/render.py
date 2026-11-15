"""CPU-only dashboard shared by the native window, PNG and demo video."""
import math
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
import numpy as np

WIDTH, HEIGHT = 1360, 900
BG = '#0b111c'
PANEL = '#131e2c'
TEXT = '#e5edf5'
MUTED = '#8d9fb5'
CYAN = '#54d8df'
GREEN = '#81e6ad'
ORANGE = '#ffc078'


@lru_cache(maxsize=16)
def font(size):
    try:
        return ImageFont.truetype('DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default()


def dashboard(world, label='baseline', size=None):
    im = Image.new('RGB', (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(im)
    def text(x,y,s,size=16,fill=TEXT):
        d.text((x,y),str(s),font=font(size),fill=fill)
    def panel(box):
        d.rounded_rectangle(box,radius=14,fill=PANEL)

    c=world.c; arm=c['arm']; target=c['target']
    text(28,18,'EXCHANGE / LAB',30)
    text(29,59,f"{target['mode'].upper()}  /  seed {c['seed']}  /  {label}  /  CPU software-in-the-loop",16,MUTED)
    text(1060,20,f'{world.time:05.1f} / {c["duration_s"]:g}s',28,CYAN)
    d.rounded_rectangle((28,91,1332,97),radius=3,fill='#26384d')
    progress=world.time/c['duration_s']
    if progress>0: d.rectangle((28,91,28+max(1,int(1304*progress)),97),fill=CYAN)

    cards=[('IN BASKET',str(world.hits),GREEN),('MISSES',str(world.misses),ORANGE),
           ('IN STORAGE',str(sum(world.inventory)),TEXT),('ARM',world.arm_state,CYAN),
           ('MEASURED',f'{100*world.measured_frames/max(1,world.frame):.0f}%',TEXT)]
    for i,(name,value,color) in enumerate(cards):
        x=28+i*264; panel((x,114,x+248,204))
        text(x+16,126,name,12,MUTED); text(x+16,148,value,28,color)

    panel((28,222,772,663)); text(46,235,'CAMERA / ALGORITHM INPUT',16)
    frame=world.sensor_image if world.sensor_image is not None else world.image
    if frame.size:
        camera=Image.fromarray(frame[:,:,::-1]).resize((704,366),Image.Resampling.BILINEAR)
        im.paste(camera,(48,273))
    d.rectangle((48,273,752,639),outline='#30455b')
    age=0 if world.sensor_stamp is None else world.time-world.sensor_stamp
    text(440,237,f"BGR  {c['camera']['width']}x{c['camera']['height']}  age {age*1000:.0f}ms",12,MUTED)
    obs=world.observation
    status='NO MEASUREMENT' if obs is None else ('MEASURED' if obs.get('measured',False) else 'COASTING')
    text(58,609,status,14,GREEN if status=='MEASURED' else ORANGE)
    if obs is not None and obs['depth']>0:
        cam=c['camera']; u=cam['focal_px']*obs['x']/obs['depth']+cam['width']/2
        v=cam['focal_px']*obs.get('y',0)/obs['depth']+cam['height']/2
        x=48+u/cam['width']*704; y=273+v/cam['height']*366
        if 48<x<752 and 273<y<639:
            d.ellipse((x-7,y-7,x+7,y+7),outline=GREEN,width=2)
        text(265,610,f"camera x {obs['x']:+.3f}m   depth {obs['depth']:.3f}m",13,MUTED)

    panel((790,222,1332,663)); text(808,235,'SCORING VIEW / GROUND TRUTH',16)
    # A planar scene: +X right, +Y forward. Camera never receives this panel.
    span=max(1.0,target['half_travel_m']+.35,abs(world.car[0])+.3)
    def point(x,y): return (1060+x/span*232, 338-y*310)
    for x in np.arange(-math.floor(span*5)/5,span,.2):
        p=point(x,-.9); q=point(x,.15); d.line((p,q),fill='#1e3043')
    for y in np.arange(-.8,.21,.2): d.line((point(-span,y),point(span,y)),fill='#1e3043')
    d.line((point(-target['half_travel_m'],0),point(target['half_travel_m'],0)),fill='#50677e',width=6)
    tx=world.target_at(world.time)
    p=point(tx-target['opening_width_m']/2,target['opening_depth_m']/2)
    q=point(tx+target['opening_width_m']/2,-target['opening_depth_m']/2)
    d.rectangle((p,q),outline=CYAN,width=3)
    text(815,272,f"rail +/-{target['half_travel_m']:.2f}m  |  {target['speed_mps']:.2f}m/s",13,MUTED)
    for shot in world.landed[-14:]:
        x,y=point(*shot['landing']); color=GREEN if shot['hit'] else '#b9715b'
        d.ellipse((x-3,y-3,x+3,y+3),fill=color)
    for shot in world.flying:
        p=min(1.,(world.time-shot['start'])/max(1e-6,shot['end']-shot['start']))
        xy=np.array(shot['point'])*(1-p)+np.array(shot['landing'])*p
        x,y=point(*xy); d.ellipse((x-6,y-6,x+6,y+6),fill=ORANGE)
    angle=world.car[2]; right=np.array([math.cos(angle),math.sin(angle)]); fwd=np.array([-math.sin(angle),math.cos(angle)])
    def body(x,y): return world.car[:2]+right*x+fwd*y
    corners=[point(*body(x,y)) for x,y in [(-.11,-.11),(.11,-.11),(.11,.11),(-.11,.11)]]
    d.polygon(corners,fill='#315269',outline=CYAN,width=2)
    tip=body(arm['emitter_x_m'],arm['emitter_forward_m'])
    slot=arm['storage_xy_m'][world.slot]
    for i,(x,y) in enumerate(arm['storage_xy_m']):
        px,py=point(*body(x,y)); d.rounded_rectangle((px-17,py-12,px+17,py+12),radius=3,fill='#233c50',outline='#7991a7')
        text(px-5,py-9,world.inventory[i],13)
    # Fixed pickup/lift path visualization; no contact-physics claim.
    location=tip
    if world.arm_state in ('PICK','LIFT'):
        duration=arm['pick_s'] if world.arm_state=='PICK' else arm['lift_s']
        p=1-min(1.,max(0.,world.arm_until-world.time)/max(duration,1e-6)); p=p*p*(3-2*p)
        storage=body(*slot)
        location=world.car[:2]*(1-p)+storage*p if world.arm_state=='PICK' else storage*(1-p)+tip*p
    elif world.arm_state=='RETURN':
        p=1-min(1.,max(0.,world.arm_until-world.time)/max(arm['return_s'],1e-6))
        location=tip*(1-p)+world.car[:2]*p
    base=point(*world.car[:2]); end=point(*location)
    d.line((base,end),fill=ORANGE,width=5)
    x,y=end; d.ellipse((x-7,y-7,x+7,y+7),fill=ORANGE if world.carry else PANEL,outline=ORANGE,width=2)
    text(811,608,'Scripted arm + ballistic drop; units: metres',12,MUTED)
    text(811,631,'Green = actual hit    Brown = actual miss',12,MUTED)

    panel((28,681,960,866)); text(46,693,'TRACKING / world X',15)
    text(675,695,'target',13,CYAN); text(769,695,'vehicle',13,ORANGE)
    x0,y0,w,h=48,733,888,104
    for fraction in (0,.5,1): d.line((x0,y0+h*fraction,x0+w,y0+h*fraction),fill='#25374a')
    if len(world.log)>1:
        for field,color in [('target_x',CYAN),('car_x',ORANGE)]:
            points=[(x0+row['time']/c['duration_s']*w,y0+h/2-row[field]/span*h/2) for row in world.log]
            d.line(points,fill=color,width=2)
    for event in world.events:
        if event['event'] in ('hit','miss'):
            x=x0+event['time']/c['duration_s']*w
            d.ellipse((x-3,847,x+3,853),fill=GREEN if event['event']=='hit' else ORANGE)
    text(48,845,'0s',11,MUTED); text(898,845,f"{c['duration_s']:g}s",11,MUTED)
    panel((978,681,1332,866)); text(996,693,'EVENTS',15)
    for i,event in enumerate(world.events[-6:]):
        color=GREEN if event['event']=='hit' else ORANGE if event['event']=='miss' else MUTED
        text(996,724+i*21,f"{event['time']:05.2f}s  {event['event'].replace('_',' ')}",13,color)
    text(29,876,'Synthetic optics / ideal odometry / scripted mechanics. Calibrate against hardware before drawing physical conclusions.',11,MUTED)
    return im.resize(size,Image.Resampling.LANCZOS) if size else im
