"""Source-only John Furrier campaign edits; explicit host coverage."""
import ast,json,math,statistics,subprocess,sys,wave,re
from pathlib import Path
import cv2,numpy as np,imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from src.media.face_detection import YuNetFaceDetector
SOURCE=ROOT/'.local/uploads/youtube-cache/NnvOJN1rg6Y/full.mp4'
OUT=ROOT/'outputs/NnvOJN1rg6Y';FF=imageio_ffmpeg.get_ffmpeg_exe()
WORDS=json.loads(SOURCE.with_suffix('.transcript_cache.json').read_text())['words']
for w in WORDS:w['text']=re.sub(r'>>\s*','',w['text']).strip()
WORDS=[w for w in WORDS if w['text'] and not re.fullmatch(r'\[[^]]+\]',w['text'])]
FONT=ImageFont.truetype(str(ROOT/'backend/fonts/Poppins-ExtraBold.ttf'),72)
tree=ast.parse((ROOT/'scripts/render_dana_shorts.py').read_text())
for node in tree.body:
 if isinstance(node,ast.FunctionDef) and node.name in ['run','stamp','make_captions']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<caption helpers>','exec'))
DET=YuNetFaceDetector();CAP=cv2.VideoCapture(str(SOURCE))
SPECS=[
 {'slug':'01-density-and-distance','title':'John Furrier breaks down AI factories','ranges':[(610.20,645.10)],'shots':[(610.20,619.80,'John Furrier',1),(619.80,635.50,'John Furrier',1.08),(635.50,645.10,'John Furrier',1)],'description':'John Furrier explains density, distance and interconnected GPUs in theCUBE NYSE interview with Will Chu and David Lazovsky.'},
 {'slug':'02-moving-intelligence','title':'John Furrier: moving intelligence, not just packets','ranges':[(1531.80,1554.35),(1601.00,1635.24)],'shots':[(1531.80,1538.537,'John Furrier',1),(1538.537,1554.35,'John Furrier',1),(1601.00,1602.034,'Will Chu',1),(1602.034,1627.459,'Will Chu',1),(1627.459,1634.366,'Will Chu',1),(1634.366,1635.24,'Will Chu',1)],'description':'John Furrier reframes AI networking; Will Chu explains why connectivity becomes the bottleneck. Same discussion, intervening remarks omitted.'}
]
def frame(t):
 CAP.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,f=CAP.read()
 if not ok:raise RuntimeError(f'No frame {t}')
 return f

def shot_crop(a,b,speaker,punch):
 samples=[]
 for t in np.linspace(a+.05,max(a+.06,b-.06),max(3,math.ceil(b-a))):
  found=DET.detect(frame(float(t)))
  if not found:continue
  if len(found)==1:f=found[0]
  elif speaker=='John Furrier':f=max(found,key=lambda f:f[0])
  else:f=min(found,key=lambda f:f[0])
  samples.append(f)
 if not samples:raise RuntimeError('No faces')
 fh=statistics.median(f[3] for f in samples)
 h=int(min(760,max(610,fh*2.25))/punch)//2*2;w=int(h*9/16)//2*2
 x=int(statistics.median(f[0]+f[2]/2 for f in samples)-w/2)//2*2
 y=int(min(790-h,max(0,min(f[1]-.28*f[3] for f in samples))))//2*2
 x=max(0,min(1920-w,x));y=max(0,y)
 return f'crop={w}:{h}:{x}:{y},scale=720:1280:flags=lanczos,setsar=1',{'x':x,'y':y,'w':w,'h':h,'samples':len(samples)}

manifest=[]
for spec in SPECS:
 work=OUT/spec['slug'];work.mkdir(exist_ok=True)
 parts=[];plans=[];counts=[];offset=0
 for i,(a,b,speaker,punch) in enumerate(spec['shots']):
  vf,plan=shot_crop(a,b,speaker,punch);n=round((b-a)*30);part=work/f'part-{i:02d}.mp4'
  run([FF,'-v','error','-y','-ss',str(a),'-i',str(SOURCE),'-an','-vf',vf+',fps=30,tpad=stop_mode=clone:stop_duration=0.15','-frames:v',str(n),'-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',str(part)])
  parts.append(part);counts.append(n);plans.append({'a':a,'b':b,'speaker':speaker,'start':offset,'end':offset+n/30,**plan});offset+=n/30
 listing=work/'concat.txt';listing.write_text('\n'.join(f"file '{p}'" for p in parts))
 pic=work/'picture.mp4';run([FF,'-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(pic)])
 chunks=[]
 for a,b in spec['ranges']:
  raw=run([FF,'-v','error','-ss',str(a),'-i',str(SOURCE),'-t',str(b-a),'-vn','-ar','48000','-ac','2','-f','f32le','pipe:1']).stdout
  chunks.append(np.frombuffer(raw,dtype='<f4').reshape(-1,2).copy())
 audio=np.concatenate(chunks);target=sum(counts)*1600
 audio=np.pad(audio,((0,max(0,target-len(audio))),(0,0)))[:target]
 wav=work/'speech.wav'
 with wave.open(str(wav),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(48000);f.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
 ass=work/'captions.ass';mapped=make_captions(spec,ass)
 label=Image.new('RGBA',(720,1280));d=ImageDraw.Draw(label);lf=ImageFont.truetype(str(ROOT/'backend/fonts/BarlowCondensed-Bold.ttf'),42)
 d.rounded_rectangle((32,58,440,125),radius=12,fill=(0,0,0,180));d.text((48,66),'JOHN FURRIER | theCUBE',font=lf,fill='white',stroke_width=1,stroke_fill='black')
 lp=work/'identity.png';label.save(lp)
 # Identity label appears only while John is the visible speaker, not over guest coverage.
 host_end=sum(p['end']-p['start'] for p in plans if p['speaker']=='John Furrier')
 graph=f"[0:v]subtitles=filename={ass}:fontsdir={ROOT/'backend/fonts'}[base];[base][2:v]overlay=0:0:enable='lt(t,{host_end})'[v]"
 final=OUT/(spec['slug']+'.mp4')
 run([FF,'-v','error','-y','-i',str(pic),'-i',str(wav),'-i',str(lp),'-filter_complex',graph,'-map','[v]','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','21','-maxrate','1800k','-bufsize','3600k','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(final)])
 probe=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(final)]).stdout)
 v=next(s for s in probe['streams'] if s['codec_type']=='video');a=next(s for s in probe['streams'] if s['codec_type']=='audio')
 assert (v['width'],v['height'])==(720,1280)
 assert abs(float(v['duration'])-float(a['duration']))<.08
 assert host_end/offset>.3
 run([FF,'-v','error','-i',str(final),'-f','null','-'])
 times=sorted(set([.25,1.5,offset-.3]+[max(0,min(offset-.1,p[k]+delta)) for p in plans for k in ['start','end'] for delta in [-.1,.1]]))
 sheet=Image.new('RGB',(1440,math.ceil(len(times)/4)*665),'#222222');d=ImageDraw.Draw(sheet)
 for i,t in enumerate(times):
  jpg=work/f'qa-{i}.jpg';run([FF,'-v','error','-y','-ss',str(t),'-i',str(final),'-frames:v','1','-vf','scale=360:640',str(jpg)])
  x=i%4*360;y=i//4*665;sheet.paste(Image.open(jpg),(x,y+25));d.text((x+5,y+5),f'{t:.3f}s',fill='white')
 sheet.save(OUT/(spec['slug']+'-review.jpg'))
 result={'path':str(final),'title':spec['title'],'duration':float(probe['format']['duration']),'host_seconds':host_end,'host_fraction':host_end/offset,'shots':plans,'ranges':spec['ranges'],'transcript':' '.join(w['text'] for w in mapped),'decode':'passed','external_audio':False,'external_footage':False}
 manifest.append(result);(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(result),flush=True)
assert len(manifest)==2
