"""Make source-specific, reviewable plans; not an automatic joke detector."""
import json,re,sys,math
from pathlib import Path
import cv2,numpy as np
R=Path(__file__).resolve().parents[1];O=R/'outputs/creator-engine/yHLNoTKOO4A';S=R/'.local/uploads/youtube-cache/yHLNoTKOO4A/full.mp4'
start,end,fps=1846.395,1854.82,24;n=round((end-start)*fps)
# Source camera boundaries reviewed from scene detection and original frames.
bounds=[start,1849.138958,1850.932417,1851.85,1853.10125,end]
sys.path.insert(0,str(R/'backend'));from src.media.face_detection import YuNetFaceDetector
cap=cv2.VideoCapture(str(S));det=YuNetFaceDetector();shots=[]
for i,(a,b) in enumerate(zip(bounds,bounds[1:])):
 fs=[]
 for t in np.linspace(a+.05,b-.05,3):
  cap.set(cv2.CAP_PROP_POS_MSEC,float(t)*1000);ok,f=cap.read();assert ok
  faces=[z for z in det.detect(f) if z[2]>=90 and z[3]>=100]
  # The small standing security guard is background context, not the selected performer.
  # When the performer's lowered face is not detected, keep the reviewed stable window.
  if faces:fs.append(max(faces,key=lambda z:z[2]*z[3]))
 assert fs,('Need manual crop review',i)
 centers=[x[0]+x[2]/2 for x in fs];cx=float(np.median(centers));x=max(0,min(1100,round(cx-410)))//2*2
 # A generous 820x1080 window protects the belt/hand action rather than face-only framing.
 for face in fs:assert x<=face[0] and face[0]+face[2]<=x+820,(i,a,b,x,fs)
 shots.append({'startFrame':round((a-start)*fps),'endFrame':round((b-start)*fps),'crop':[x,0,820,1080],'reviewed':True,'sourceRange':[a,b],'emphasisZoom':i in [0,4],'reason':'Original source camera cut; face-assisted window manually reviewed for gestures. Not speaker identification.'})
cap.release()
d=json.loads((R/'.local/uploads/youtube-cache/yHLNoTKOO4A/full.en-orig.json3').read_text());raw=[]
for e in d['events']:
 if e.get('aAppend'):continue
 for seg in e.get('segs',[]):
  text=seg.get('utf8','').replace('>>','').strip();t=(e['tStartMs']+seg.get('tOffsetMs',0))/1000
  if text:raw.append({'text':text,'start':t})
raw.sort(key=lambda x:x['start']);words=[]
for i,w in enumerate(raw):
 if not start<=w['start']<end:continue
 text=w['text']
 if re.fullmatch(r'\[\s*_+\s*\]',text):text='N****' # source word independently recognized by local Whisper; mask caption only.
 if text.startswith('['):continue
 tokens=text.split();a=w['start']-start;b=min(n/fps,(raw[i+1]['start'] if i+1<len(raw) else end)-start,a+.7)
 for k,tok in enumerate(tokens):words.append({'text':tok.upper(),'start':round(a+(b-a)*k/len(tokens),6),'end':min(n/fps,round(a+(b-a)*(k+1)/len(tokens),6))})
for i in range(len(words)-1):words[i]['end']=min(words[i]['end'],words[i+1]['start'])
assert all(w['end']>w['start'] for w in words)
c={'version':1,'source':str(S),'sourceUrl':'https://www.youtube.com/watch?v=yHLNoTKOO4A','sourceWidth':1920,'sourceHeight':1080,'start':start,'end':end,'width':1080,'height':1920,'fps':fps,'fontPath':str(R/'backend/fonts/Poppins-ExtraBold.ttf'),'outputDir':str(O/'respect-your-elders'),'contentType':'sketch-comedy / audition reactions, NOT gaming','editorial':{'opening':'Druski asks his elder not to raise his voice.','setup':'Assertive verbal challenge, with visible genuine expression.','escalation':'The contestant threatens the belt and reaches toward his waistband.','payoff':'Druski immediately backs down: All right, you got it.','ending':'Before the unrelated Rudy Ray Moore discussion and next camera cut.','limitations':['One source camera shot cuts the top of Druski’s head as he recoils; the edit cannot restore absent source pixels.','Source audio retained; one colloquial slur masked in visible captions only.','Original brief reaction camera cuts retained for genuine comedic timing; not transplanted reactions.']},'shots':shots,'words':words,'graphics':{'caption':{'position':.64,'maxWords':3},'headline':{'text':'INSTANT REGRET','start':0,'end':1.4,'x':.5,'y':.135,'color':'#FFFFFF','fontSizeRatio':.074},'emphasis':{'keywords':['elder','belt','up','right']}},'postCaption':'He said “don’t raise your voice”… then the belt entered the conversation. 😂\n\nDruski vs an old head who wasn’t having it.\n\n#Druski #CouldaBeenRecords #ComedyClips #FunnyMoments #RespectYourElders'}
save=O/'clip-plan.json';save.write_text(json.dumps(c,indent=2));print('Plan',n,'frames',n/fps,'seconds',len(words),'words');print(' '.join(w['text'] for w in words));print(shots)
