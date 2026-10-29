"""Create reviewed source-specific plans for the reusable podcast CLI."""
import datetime,json,math,statistics,sys
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'outputs/premium-dana';sys.path.insert(0,str(R/'backend'))
from src.media.face_detection import YuNetFaceDetector
S=R/'.local/uploads/youtube-cache/Q-DFC0AnbY4/full.mp4';cap=cv2.VideoCapture(str(S));det=YuNetFaceDetector()
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
base={'version':1,'source':{'path':str(S),'url':'https://youtu.be/Q-DFC0AnbY4?is=rIqehB23FVSC4hHE'},'transcript':{'path':str(O/'reviewed-source-transcript.json'),'units':'milliseconds'},'outputDir':str(O/'renders'),'fontPath':str(R/'backend/fonts/Poppins-ExtraBold.ttf'),'width':1080,'height':1920,'fps':30,'crf':19,'renderOptions':{'renderOptions':{'crf':18,'muted':True,'audioBitrate':'192k'}},'clips':[]}
items=[
('01-time-freedom',[[706.25,714.15],[673.834,686.24]],[(0,706.25,714.15,784,None),(1,673.834,678,1080,None),(1,678,682.25001,964,None),(1,682.25001,686.24,858,None)],'WANT MORE\nFREE TIME? DON’T\nSTART A BUSINESS.','Business freedom costs holidays; satisfying final nuance: when you like the work, it is fun.','Starting a business for more freedom? Be prepared to have less of it first.\n\nDana White on the reality behind being your own boss.\n\nWhat surprised you most about working for yourself?\n\n#DanaWhite #Entrepreneurship #BusinessOwner #FounderLife #BusinessReality',7.9,['birthdays','Christmas','Thanksgivings']),
('02-build-the-team',[[1223.87,1225.84],[1225.84,1258.72]],[(0,1223.87,1225.84,880,None),(1,1225.84,1235.84,984,None),(1,1235.84,1243.04,894,None),(1,1243.04,1248.32,984,None),(1,1248.32,1258.72,894,1258.50)],'YOU CAN’T DO\nEVERYTHING.\nBUILD A TEAM.','The early everything-guy story resolves in identifying the right people as his superpower.','You can wear every hat at the start. You cannot build everything alone.\n\nDana White on the skill that helped him build a team: choosing the right people.\n\nWhat do you look for in someone you work with?\n\n#DanaWhite #Leadership #TeamBuilding #Entrepreneurship #BusinessLessons',59/30,[]),
('03-quit-drinking',[[237.02,243.2],[243.2,257.14],[258.50,266.84]],[(0,237.02,243.2,1080,None),(1,243.2,248.625,984,None),(1,248.625,252.083333,1000,None),(1,252.083333,257.14,1080,None),(2,258.50,263.6,1080,None),(2,263.6,266.84,984,None)],'I QUIT DRINKING\nAT 21.','Dana explains the personal ambition and family experiences behind quitting at 21; closes with the cost he saw alcohol have on talented relatives.','“I quit drinking when I was 21.”\n\nDana White shares the personal reasons behind that decision and what he learned from the people around him.\n\nWhat habit have you changed to protect your future?\n\n#DanaWhite #PersonalGrowth #Habits #SelfDiscipline #PodcastClips',185/30,[])
]
reviews=[]
for slug,ranges,shots,headline,payoff,post,cut,strikes in items:
 plans=[]
 for ri,a,b,h,videoend in shots:
  fs=[]
  for t in np.linspace(a+.06,(videoend or b)-.08,max(2,math.ceil((b-a)/1.5))):
   cap.set(cv2.CAP_PROP_POS_MSEC,float(t)*1000);ok,f=cap.read()
   if not ok:raise RuntimeError(('decode',t))
   faces=det.detect(f)
   if len(faces)!=1:raise RuntimeError(('ambiguous face',t,len(faces)))
   fs.append((float(t-a),faces[0]))
  h=int(min(1080,h))//2*2;w=int(h*9/16)//2*2
  y=max(0,min(1080-h,int(min(f[1]-.45*f[3] for _,f in fs))))//2*2
  track=[]
  for i,(t,f) in enumerate(fs):
   x=statistics.mean(z[0]+z[2]/2-w/2 for _,z in fs[max(0,i-1):i+2]);x=max(0,min(1920-w,x))
   # Constrain smoothing to retain the current face plus a small lateral margin.
   lo=max(0,f[0]+f[2]+16-w);hi=min(1920-w,f[0]-16)
   if lo>hi:raise RuntimeError(('face wider than safe portrait crop',slug,t))
   x=max(lo,min(hi,x))
   track.append({'time':round(t,6),'x':round(x,4),'y':y})
   if f[0]<x or f[0]+f[2]>x+w or f[1]<y:raise RuntimeError(('face safety',slug,t,tuple(f),x,y,w,h))
  plan={'rangeIndex':ri,'start':a,'end':b,'mode':'crop','reviewed':True,'crop':{'x':track[0]['x'],'y':y,'width':w,'height':h},'track':track}
  if videoend:plan['videoEnd']=videoend
  plans.append(plan)
  for t in [a+.1,(a+(videoend or b))/2,(videoend or b)-.1]:
   cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,f=cap.read();assert ok
   xs=np.interp(t-a,[p['time'] for p in track],[p['x'] for p in track]);x=int(xs)
   img=Image.fromarray(cv2.cvtColor(f[y:y+h,x:x+w],cv2.COLOR_BGR2RGB));img=img.resize((216,384));reviews.append((f'{slug} {t:.2f}s',img))
 clip={'id':slug,'ranges':ranges,'shots':plans,'approval':{'approved':True,'reviewer':'Hermes editorial selection under K request; render visual review still pending','reviewedAt':now},'captions':{'style':'bold','headlineDuration':min(3.6,cut-.1),'headlineAccent':'#FFE000','strikeWords':strikes},'headline':headline,'sourceNotes':'Manually reviewed source coverage, one visible speaker in selected shots, smoothed face-assisted crops reset at camera cuts; face detection is not speaker recognition. No quote-card inserts.','payoff':payoff,'postCaption':post,'riser':{'path':str(R/'outputs/assets/KiJX7agcIns.wav'),'crestSeconds':1.78,'cutSeconds':cut,'gain':.28,'semanticNote':'End of complete spoken opening statement; purposefully edited range boundary.'},'renderOptions':{'transitions':[{'time':cut,'rise':.1,'fall':8/30,'color':'#FFFFFF','opacity':1}]}}
 base['clips'].append(clip)
cap.release()
cols=6;rows=math.ceil(len(reviews)/cols);sheet=Image.new('RGB',(cols*216,rows*410),'#141414');d=ImageDraw.Draw(sheet)
for i,(label,img) in enumerate(reviews):x=i%cols*216;y=i//cols*410;sheet.paste(img,(x,y+26));d.text((x+3,y+5),label,fill='white')
sheet.save(O/'crop-plan-review.jpg');(O/'pipeline.json').write_text(json.dumps(base,indent=2));print('Saved',len(base['clips']),'planned edits and',len(reviews),'crop samples',flush=True)
