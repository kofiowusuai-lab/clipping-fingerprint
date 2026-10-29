"""Catch isolated Remotion picture corruption by comparing every source frame.
Captions/headlines are outside the measured centre-picture band.
"""
import argparse,json
from pathlib import Path
import cv2,numpy as np
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('render',type=Path);p.add_argument('--report',type=Path,required=True);p.add_argument('--max-mae',type=float,default=6);p.add_argument('--skip-frame-start',type=int,default=-1);p.add_argument('--skip-frame-end',type=int,default=-1);p.add_argument('--band-top',type=float,default=.24);p.add_argument('--band-bottom',type=float,default=.68);a=p.parse_args()
if not 0<=a.band_top<a.band_bottom<=1:p.error('Invalid comparison band')
s=cv2.VideoCapture(str(a.source));r=cv2.VideoCapture(str(a.render));scores=[];i=0
while True:
 ok,x=s.read();good,y=r.read()
 if not ok and not good:break
 if not ok or not good:raise RuntimeError(f'Frame count differs at {i}')
 if x.shape!=y.shape:raise RuntimeError('Frame dimensions differ')
 h,w=x.shape[:2];band=(slice(round(h*a.band_top),round(h*a.band_bottom)),slice(round(w*.08),round(w*.92)))
 mae=float(cv2.absdiff(x[band],y[band]).mean());scores.append({'frame':i,'mae':mae});i+=1
assert scores,'No decoded frames'
bad=[x for x in scores if x['mae']>a.max_mae and not a.skip_frame_start<=x['frame']<=a.skip_frame_end]
report={'source':str(a.source),'render':str(a.render),'frames_compared':i,'intentional_effect_frame_range':[a.skip_frame_start,a.skip_frame_end] if a.skip_frame_start>=0 else None,'threshold':a.max_mae,'bad_frames':bad,'worst_frames':sorted(scores,key=lambda x:x['mae'],reverse=True)[:12],'passed':not bad}
a.report.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if bad:raise SystemExit(1)
