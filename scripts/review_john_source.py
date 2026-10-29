import cv2,json
from PIL import Image,ImageDraw
from pathlib import Path
R=Path(__file__).resolve().parents[1];p=R/'.local/uploads/youtube-cache/NnvOJN1rg6Y';c=cv2.VideoCapture(str(p/'full.mp4'))
times=[20,35,60,602,610,620,630,640,650,660,1518,1530,1535,1540,1548,1553,1599,1605,1615,1625,1634,1740,1765,1780]
sheet=Image.new('RGB',(1600, len(range(0,len(times),4))*250),'#202020');d=ImageDraw.Draw(sheet)
for i,t in enumerate(times):
 c.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,f=c.read();assert ok
 im=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB));im.thumbnail((400,225));x=i%4*400;y=i//4*250;sheet.paste(im,(x,y+25));d.text((x+5,y+5),str(t),fill='white')
sheet.save(R/'outputs/NnvOJN1rg6Y/source-review.jpg')
w=json.loads((p/'full.transcript_cache.json').read_text())['words']
for a,b in [(600,658),(1517,1558),(1598,1637)]:print(a,b,[(x['start']/1000,x['text']) for x in w if a*1000<=x['start']<b*1000])
print('size',c.get(3),c.get(4))
