"""Additional real-output gates: every-frame picture, luma envelope, audio sync and review sheets."""
import json,math,subprocess,sys
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from scipy.signal import correlate,correlation_lags
R=Path(__file__).resolve().parents[1];O=R/'outputs/premium-dana';c=json.loads((O/'pipeline.json').read_text())
def run(a):return subprocess.run([str(x) for x in a],capture_output=True,check=True)
def audio(p):return np.frombuffer(run(['ffmpeg','-v','error','-i',p,'-vn','-ar','48000','-ac','1','-f','f32le','pipe:1']).stdout,dtype='<f4').astype('float64')
reports=[]
for clip in c['clips']+[dict(c['clips'][0],id='01-time-freedom-clean')]:
 W=O/'renders'/clip['id'];B=O/'renders'/('01-time-freedom' if clip['id'].endswith('-clean') else clip['id']);F=W/'final.mp4';assert F.exists(),F
 cut=clip['riser']['cutSeconds'];lo=math.floor((cut-.1)*30);hi=math.ceil((cut+8/30)*30)
 result=run([sys.executable,R/'scripts/check_remotion_frames.py',B/'picture.mp4',F,'--report',W/'all-frame-comparison.json','--skip-frame-start',lo,'--skip-frame-end',hi,'--band-top',.26,'--band-bottom',.58]);print(result.stdout.decode(),flush=True)
 cap=cv2.VideoCapture(str(F));fps=cap.get(cv2.CAP_PROP_FPS);frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));duration=frames/fps
 def frame(t):
  cap.set(cv2.CAP_PROP_POS_FRAMES,round(t*fps));ok,f=cap.read();assert ok,(F,t);return f
 peak=frame(cut);assert float(peak.mean())>249 and float(peak.std())<2,('white bloom',F,peak.mean(),peak.std())
 luma={'peakFrame':round(cut*fps),'mean':float(peak.mean()),'std':float(peak.std()),'riseFrames':3,'recoveryFrames':8,'intentionalFrameExclusion':[lo,hi]}
 source=audio(B/'normalized.wav');encoded=audio(F);n=min(len(source),len(encoded));source=source[:n:48];encoded=encoded[:n:48];source-=source.mean();encoded-=encoded.mean()
 cor=correlate(encoded,source,mode='full',method='fft');lags=correlation_lags(len(encoded),len(source));sel=np.abs(lags)<=100;lag=int(lags[sel][np.argmax(cor[sel])]);rho=float(np.corrcoef(source,encoded)[0,1]);assert abs(lag)<=2 and rho>.98,('audio sync',lag,rho)
 times=[.05,.8,1.6,3,4.7,cut-.1333,cut,cut+.1,cut+.4,duration*.5,duration*.72,duration-1,duration-.2]
 if clip['id'].startswith('01'):
  words=json.loads((B/'words.json').read_text());times += [w['start']+.15 for w in words if w['text'].lower().strip('.,') in ['birthdays','christmas','thanksgivings']]
 times=sorted(set(max(0,min(duration-1/fps,t)) for t in times));cols=4;sheet=Image.new('RGB',(cols*360,math.ceil(len(times)/cols)*670),'#151515');draw=ImageDraw.Draw(sheet)
 for i,t in enumerate(times):
  im=Image.fromarray(cv2.cvtColor(frame(t),cv2.COLOR_BGR2RGB)).resize((360,640));x=i%cols*360;y=i//cols*670;sheet.paste(im,(x,y+30));draw.text((x+8,y+7),f'{t:.3f}s',fill='white')
 sheet.save(W/'editorial-review.jpg');cap.release()
 a={'audioLagMilliseconds':lag,'audioCorrelationVsNormalized':rho,'luma':luma,'frames':frames,'duration':duration,'allFramePictureComparison':json.loads((W/'all-frame-comparison.json').read_text()),'visualReview':'pending: inspect actual saved render frames before approval'}
 (W/'additional-qa.json').write_text(json.dumps(a,indent=2));reports.append({'id':clip['id'],'frames':frames,'duration':duration,'audioLagMilliseconds':lag,'audioCorrelation':rho})
(O/'technical-summary.json').write_text(json.dumps(reports,indent=2));assert len(reports)==4;print(json.dumps(reports,indent=2),flush=True)
