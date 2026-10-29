"""Inspect genuine source faces/camera cuts before selecting creator crops."""
import json,sys
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'outputs/creator-engine/yHLNoTKOO4A';sys.path.insert(0,str(R/'backend'))
from src.media.face_detection import YuNetFaceDetector
S=R/'.local/uploads/youtube-cache/yHLNoTKOO4A/full.mp4';cap=cv2.VideoCapture(str(S));det=YuNetFaceDetector()
times=[1845.4,1847.4,1849.5,1851.2,1852.2,1853.6,1854.6];rows=[];sheet=Image.new('RGB',(7*300,2*560),'#121212');draw=ImageDraw.Draw(sheet)
for i,t in enumerate(times):
 cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,f=cap.read();assert ok
 faces=det.detect(f);faces.sort(key=lambda z:z[2]*z[3],reverse=True);assert faces
 face=faces[0];cx=face[0]+face[2]/2;box=[max(0,min(1920-608,round(cx-304))),0,608,1080];x,y,w,h=box
 for row,b in enumerate([box,[max(0,min(1920-820,round(cx-410))),0,820,1080]]):
  x,y,w,h=b;img=Image.fromarray(cv2.cvtColor(f[y:y+h,x:x+w],cv2.COLOR_BGR2RGB));img.thumbnail((300,530));xx=i*300+(300-img.width)//2;yy=row*560+30;sheet.paste(img,(xx,yy));draw.text((i*300+5,row*560+7),f'{t:.2f}s / width{w}',fill='white')
 rows.append({'time':t,'faces':faces,'crop608':box,'crop820':[max(0,min(1920-820,round(cx-410))),0,820,1080]})
sheet.save(O/'crop-comparison.jpg');(O/'face-review.json').write_text(json.dumps(rows,indent=2));cap.release();print(json.dumps(rows,indent=2))
