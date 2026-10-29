"""Visual/motion QA for the requested holiday strike pass."""
import json,cv2,numpy as np
from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'outputs/podcast-inline-strikes';SRC=R/'outputs/podcast-hook-tests/A-yellow.mp4';FINAL=O/'A-yellow-inline-strikes.mp4'
s=cv2.VideoCapture(str(SRC));r=cv2.VideoCapture(str(FINAL));scores=[];i=0
while True:
 ok,a=s.read();good,b=r.read()
 if not ok and not good:break
 assert ok and good
 # The inline captions remain in the original lower third; compare the untouched picture above it.
 delta=float(cv2.absdiff(a[307:819,58:662],b[307:819,58:662]).mean());scores.append(delta);i+=1
assert i==610 and max(scores)<6,(i,max(scores))
frames=[258,261,267,288,291,295,312,315,319,343,351,354]
sheet=Image.new('RGB',(1440,2010),'#222');d=ImageDraw.Draw(sheet)
for j,n in enumerate(frames):
 r.set(cv2.CAP_PROP_POS_FRAMES,n);ok,f=r.read();assert ok
 im=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB));im.thumbnail((360,640));x=j%4*360;y=j//4*670;sheet.paste(im,(x,y+25));d.text((x+5,y+5),f'{n/30:.3f}s / {n}',fill='white')
sheet.save(O/'motion-review.jpg')
report={'frames_checked':i,'untouched_picture_band':[307,819],'max_picture_mae':max(scores),'picture_check':'passed','review_frames':frames}
(O/'frame-qa.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

