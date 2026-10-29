"""Creator clips: Remotion transparent graphics + one FFmpeg picture encode.

The editor supplies reviewed source ranges/crops. No game-event or speaker-ID claim.
"""
import argparse,hashlib,json,math,re,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1]
def run(a):
 p=subprocess.run([str(x) for x in a],capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-5000:])
 return p

def probe(p):return json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',p]).stdout)
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,allow_nan=False))
def validate(c):
 if c.get('version')!=1:raise ValueError('version must be 1')
 src=Path(c['source']).resolve(strict=True);out=Path(c['outputDir']).resolve()
 if src==out or out in src.parents:raise ValueError('Outputs cannot contain source')
 if not 0<=c['start']<c['end']:raise ValueError('Invalid source range')
 if c['fps'] not in [24,30] or c['width']%2 or c['height']%2:raise ValueError('Invalid output geometry')
 n=round((c['end']-c['start'])*c['fps']);cursor=0
 for s in c['shots']:
  if s['startFrame']!=cursor or not s['startFrame']<s['endFrame']<=n:raise ValueError('Shots must partition edited frames')
  if not s.get('reviewed'):raise ValueError('Source crops require actual review')
  x,y,w,h=s['crop']
  if min(x,y)<0 or min(w,h)<=0:raise ValueError('Invalid crop')
  cursor=s['endFrame']
 if cursor!=n:raise ValueError('Shots do not cover clip')
 return n

def normalized_audio(c,w,n):
 wav=w/'normalized.wav';duration=n/c['fps'];prefix=['ffmpeg','-hide_banner','-ss',c['start'],'-i',c['source'],'-t',duration,'-vn']
 target='loudnorm=I=-16:TP=-1.5:LRA=11'
 logs=run(prefix+['-af',target+':print_format=json','-f','null','-']).stderr.decode();m=json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}',logs,re.S)[-1])
 if not math.isfinite(float(m['input_i'])):raise ValueError('Silent audio')
 fil=target+''.join(f':{a}={m[b]}' for a,b in [('measured_I','input_i'),('measured_TP','input_tp'),('measured_LRA','input_lra'),('measured_thresh','input_thresh'),('offset','target_offset')])+':linear=true:print_format=json'
 p=run(prefix+['-y','-af',fil,'-ar','48000','-ac','2','-c:a','pcm_s24le',wav]);m2=json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}',p.stderr.decode(),re.S)[-1]);save(w/'audio-normalization.json',{'pass1':m,'pass2':m2,'denoising':False,'addedMusic':False,'addedSfx':False});return wav

def build_graph(c,preset,n):
 width,height,fps=c['width'],c['height'],c['fps'];shots=c['shots'];sw,sh=c['sourceWidth'],c['sourceHeight'];graph=[]
 graph.append(f'[0:v]fps={fps},trim=end_frame={n},setpts=PTS-STARTPTS,split={len(shots)}'+''.join(f'[s{i}]' for i in range(len(shots))))
 for i,s in enumerate(shots):
  x,y,cw,ch=s['crop']
  if x+cw>sw or y+ch>sh:raise ValueError('Crop outside source')
  graph.append(f'[s{i}]trim=start_frame={s["startFrame"]}:end_frame={s["endFrame"]},setpts=PTS-STARTPTS,split=2[b{i}][f{i}]')
  graph.append(f'[b{i}]scale=180:320:force_original_aspect_ratio=increase,crop=180:320,boxblur=8:1,eq=brightness=-0.10:saturation=0.65,scale={width}:{height}:flags=bilinear[bg{i}]')
  fh=round(width*ch/cw)//2*2;top=(height-fh)//2
  if fh>height:raise ValueError('Foreground is taller than portrait canvas')
  filt=f'crop={cw}:{ch}:{x}:{y},scale={width}:{fh}:flags=lanczos,setsar=1'
  if preset=='aggressive' and s.get('emphasisZoom',False):
   filt+=f",zoompan=z='1+0.035*sin(PI*min(on/5,1)/2)':x='iw/2-iw/zoom/2':y='ih*0.25-ih*0.25/zoom':d=1:s={width}x{fh}:fps={fps}"
  graph.append(f'[f{i}]{filt}[fg{i}]');graph.append(f'[bg{i}][fg{i}]overlay=0:{top}:shortest=1,setsar=1[v{i}]')
 graph.append(''.join(f'[v{i}]' for i in range(len(shots)))+f'concat=n={len(shots)}:v=1:a=0[base]')
 graph.append(f'[base]fps={fps},settb=1/{fps},setpts=N/({fps}*TB),tpad=stop_mode=clone:stop_duration=0.1,trim=end_frame={n}[timed]')
 graph.append('[timed][1:v]overlay=0:0:eof_action=repeat:shortest=0:format=auto,format=yuv420p[v]');return ';'.join(graph)

def qa(c,w,n,final):
 p=probe(final);v=next(s for s in p['streams'] if s['codec_type']=='video');a=next(s for s in p['streams'] if s['codec_type']=='audio')
 from fractions import Fraction
 assert(v['width'],v['height'])==(c['width'],c['height']);assert v['codec_name']=='h264' and a['codec_name']=='aac';assert int(v['nb_frames'])==n;assert abs(float(v['duration'])-float(a['duration']))<.06
 assert float(Fraction(v['avg_frame_rate']))==c['fps'],'Output frame rate differs from edit plan'
 assert abs(float(v['duration'])-n/c['fps'])<.02 and abs(float(a['duration'])-n/c['fps'])<.06,'Output timeline duration differs from edit plan'
 run(['ffmpeg','-v','error','-xerror','-i',final,'-f','null','-'])
 raw=run(['ffmpeg','-v','error','-i',final,'-vn','-ar','48000','-ac','1','-f','f32le','pipe:1']).stdout;audio=np.frombuffer(raw,dtype='<f4');assert audio.size and float(np.sqrt(np.mean(audio**2)))>.001
 source=run(['ffmpeg','-v','error','-i',w/'normalized.wav','-vn','-ar','48000','-ac','1','-f','f32le','pipe:1']).stdout;ref=np.frombuffer(source,dtype='<f4');m=min(len(ref),len(audio));corr=float(np.corrcoef(ref[:m:48],audio[:m:48])[0,1]);assert corr>.98,('audio mismatch',corr)
 logs=run(['ffmpeg','-hide_banner','-i',final,'-vf','blackdetect=d=0.1:pix_th=0.10:pic_th=0.98','-af','silencedetect=n=-45dB:d=0.5','-f','null','-']).stderr.decode();flags=[x.strip() for x in logs.splitlines() if 'black_start:' in x or 'silence_start:' in x or 'silence_end:' in x]
 import cv2
 duration=n/c['fps'];times=sorted({0,.6,1.2,duration*.35,duration*.55,duration*.75,duration-.4,duration-1/c['fps'],*[s['startFrame']/c['fps'] for s in c['shots'][1:]]})
 wanted={max(0,min(n-1,round(t*c['fps']))):t for t in times};review={}
 cap=cv2.VideoCapture(str(final));luma=[];freeze=[];previous=None;streak=0;i=0
 while True:
  ok,f=cap.read()
  if not ok:break
  if i in wanted:review[i]=Image.fromarray(cv2.cvtColor(cv2.resize(f,(324,576)),cv2.COLOR_BGR2RGB))
  gray=cv2.cvtColor(cv2.resize(f,(64,114)),cv2.COLOR_BGR2GRAY);luma.append(float(gray.mean()))
  if previous is not None and float(np.abs(gray.astype('float32')-previous.astype('float32')).mean())<.05:streak+=1
  else:
   if streak>=c['fps']/2:freeze.append({'endingFrame':i-1,'frames':streak})
   streak=0
  previous=gray;i+=1
 cap.release();assert i==n;assert min(luma)>5
 assert set(review)==set(wanted),'Missing representative decoded frames'
 sheet=Image.new('RGB',(4*324,math.ceil(len(times)/4)*600),'#151515');draw=ImageDraw.Draw(sheet)
 import io
 for k,index in enumerate(sorted(review)):
  im=review[index];t=index/c['fps'];x=k%4*324;y=k//4*600;sheet.paste(im,(x,y+24));draw.text((x+5,y+5),f'{t:.3f}s',fill='white')
 sheet.save(w/'contact-sheet.jpg');report={'file':str(final),'width':v['width'],'height':v['height'],'fps':v['avg_frame_rate'],'duration':duration,'frames':n,'fullDecode':'passed','audioCorrelationVsNormalized':corr,'audioPeak':float(np.abs(audio).max()),'blackSilenceFlags':flags,'freezeFlags':freeze,'everyFrameDecoded':i,'minimumMeanLuma':min(luma),'visualReview':'pending','deliveryReady':False};save(w/'qa.json',report);return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--preset',choices=['clean-energy','aggressive'],default='clean-energy');p.add_argument('--stage',choices=['render','composite','qa'],default='render');args=p.parse_args()
 args.plan=args.plan.expanduser().resolve(strict=True)
 c=json.loads(args.plan.read_text())
 for key in ('source','outputDir','fontPath'):
  value=Path(c[key]).expanduser()
  c[key]=str((value if value.is_absolute() else args.plan.parent/value).resolve())
 n=validate(c);w=Path(c['outputDir'])/args.preset;w.mkdir(parents=True,exist_ok=True);final=w/'final.mp4'
 if args.stage=='qa':print(json.dumps(qa(c,w,n,final),indent=2));return
 # Graphics never decode the picture. The original source is encoded only once below.
 job=dict(c['graphics']);job.update({'outputDir':str((w/'graphics').resolve()),'fontPath':c['fontPath'],'width':c['width'],'height':c['height'],'fps':c['fps'],'durationInFrames':n,'preset':args.preset,'words':c['words']})
 if args.stage=='render':
  save(w/'graphics.job.json',job);normalized_audio(c,w,n)
  subprocess.run(['node',str(R/'remotion/render-creator.mjs'),str(w/'graphics.job.json')],check=True)
 else:
  prior=json.loads((w/'graphics.job.json').read_text());assert prior==job,'Graphics configuration changed; render to a fresh output folder'
  manifest=json.loads((w/'graphics/manifest.json').read_text());assert manifest['frameCount']==n and manifest['fps']==c['fps']
  assert (w/'normalized.wav').exists()
 graphics=w/'graphics';images=sorted(graphics.glob('*.png'));assert len(images)==n,(len(images),n)
 # Remotion emits zero-padded names, so a glob preserves edited-timeline order.
 graph=build_graph(c,args.preset,n);(w/'filtergraph.txt').write_text(graph)
 run(['ffmpeg','-v','error','-y','-threads','2','-ss',c['start'],'-i',c['source'],'-framerate',c['fps'],'-pattern_type','glob','-i',str(graphics/'*.png'),'-i',w/'normalized.wav','-filter_complex_threads','1','-filter_complex_script',w/'filtergraph.txt','-map','[v]','-map','2:a:0','-frames:v',n,'-r',c['fps'],'-fps_mode','cfr','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',final])
 print(json.dumps(qa(c,w,n,final),indent=2));(w/'post-caption.txt').write_text(c['postCaption']+'\n')
if __name__=='__main__':main()
