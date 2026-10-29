"""Restore onset audio, add requested riser/clicks and restrained cut flashes."""
import ast
import json
import math
import subprocess
import wave
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/serhant-v3'; OUT.mkdir(exist_ok=True)
OLD=ROOT/'outputs/serhant-v2'
SRC=ROOT/'.local/uploads/youtube-cache/K213Pn9ffIc/full.mp4'
FF=imageio_ffmpeg.get_ffmpeg_exe()
RATE=48000
beats=[(402.75,406.56,1.1),(450.12,456.18,1),(466.14,472.88,1),(472.88,480.02,1.13),(480.02,486.88,1),(486.88,488.76,1.16)]
counts=[round((b-a)*30) for a,b,_ in beats]
starts=np.cumsum([0]+[n/30 for n in counts]).tolist()

def run(args):
    r=subprocess.run(args,capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode()[-6000:])
    return r

# Emit exact frame counts per shot; prevent an AAC concat delay at every edit.
video=OUT/'picture.mp4'
p=subprocess.Popen([FF,'-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','720x1280','-r','30','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',str(video)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
for i,n in enumerate(counts):
    cap=cv2.VideoCapture(str(OLD/'03-setbacks-recut'/f'part-{i:02d}.mp4'))
    frames=[]
    while True:
        ok,f=cap.read()
        if not ok: break
        frames.append(f)
    cap.release()
    assert frames
    if i==0:
        # Source cuts to the listener on the final two hook frames. Hold the
        # preceding guest frame for those 67ms; keep the original spoken audio.
        for j in range(100,len(frames)): frames[j]=frames[99].copy()
        frames=[frames[0]]*round((403.14-402.75)*30)+frames
    for j in range(n): p.stdin.write(frames[min(j,len(frames)-1)].tobytes())
p.stdin.close(); error=p.stderr.read(); assert p.wait()==0,error.decode()

# Decode speech straight from source as PCM, preserving the complete initial S.
audio_parts=[]
for i,(a,b,_) in enumerate(beats):
    raw=run([FF,'-v','error','-ss',str(a),'-i',str(SRC),'-t',str(b-a),'-vn','-ar',str(RATE),'-ac','2','-f','f32le','pipe:1']).stdout
    x=np.frombuffer(raw,dtype='<f4').reshape(-1,2).copy()
    length=counts[i]*1600
    if len(x)<length: x=np.pad(x,((0,length-len(x)),(0,0)))
    audio_parts.append(x[:length])
speech=np.concatenate(audio_parts)
fx=np.zeros_like(speech)
rng=np.random.default_rng(28)
# A restrained upward pitch/noise sweep, ending at the start of 'speed'.
a,end=.65,404.64-402.75
n=round((end-a)*RATE); t=np.arange(n)/RATE; u=t/(n/RATE)
freq=180*np.power(10,u)
phase=np.cumsum(freq)/RATE*2*np.pi
noise=rng.normal(size=n)
noise=np.convolve(noise,np.array([1,-1])/2,mode='same')
env=(np.sin(np.pi*u/2)**2)*np.minimum(1,(1-u)*35)
riser=(np.sin(phase)*.010+noise*.007)*env
idx=round(a*RATE); fx[idx:idx+n]+=riser[:,None]
# Short click at each editorial cut; no sound on tiny source camera changes.
for cut in starts[1:-1]:
    n=round(.035*RATE); t=np.arange(n)/RATE
    click=(rng.normal(size=n)*.018*np.exp(-t*450)+np.sin(2*np.pi*1800*t)*.014*np.exp(-t*170))
    idx=round(cut*RATE); fx[idx:idx+n]+=click[:,None]
mix=speech+fx
peak=float(np.abs(mix).max())
if peak>.95: mix*=.95/peak
wav=OUT/'speech-and-effects.wav'
with wave.open(str(wav),'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(RATE); w.writeframes((np.clip(mix,-1,1)*32767).astype('<i2').tobytes())

# Rebuild word timings against the revised start; never shift baked captions.
WORDS=json.loads(SRC.with_suffix('.transcript_cache.json').read_text())['words']
FONT=ImageFont.truetype(str(ROOT/'backend/fonts/Poppins-ExtraBold.ttf'),60)
tree=ast.parse((ROOT/'scripts/render_serhant_v2.py').read_text())
functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ['stamp','captions']]
exec(compile(ast.Module(body=functions,type_ignores=[]),'<caption_helpers>','exec'))
ass=OUT/'captions.ass'; captions({'beats':beats},ass)
# A low-opacity, two-frame flash at the deliberate edits, not rapid strobing.
vf=f'subtitles=filename={ass}:fontsdir={ROOT/"backend/fonts"}'
for cut in starts[1:-1]:
    vf+=f",drawbox=x=0:y=0:w=iw:h=ih:color=white@0.16:t=fill:enable='between(t,{cut:.5f},{cut+1/30-.001:.5f})'"
    vf+=f",drawbox=x=0:y=0:w=iw:h=ih:color=white@0.07:t=fill:enable='between(t,{cut+1/30:.5f},{cut+2/30-.001:.5f})'"
output=OUT/'03-setbacks-riser-clicks.mp4'
graph=f"[0:v]{vf}[base];[base][2:v]overlay=0:0:enable='lt(t,3.6)'[v]"
run([FF,'-v','error','-y','-i',str(video),'-i',str(wav),'-i',str(OLD/'03-hero-overlay.png'),'-filter_complex',graph,'-map','[v]','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','20','-maxrate','1800k','-bufsize','3600k','-pix_fmt','yuv420p','-af','alimiter=limit=0.95:level=false','-c:a','aac','-b:a','128k','-movflags','+faststart',str(output)])
probe=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]).stdout)
vs=next(s for s in probe['streams'] if s['codec_type']=='video'); aus=next(s for s in probe['streams'] if s['codec_type']=='audio')
assert abs(float(vs['duration'])-float(aus['duration']))<.05
assert (vs['width'],vs['height'])==(720,1280)
assert not run([FF,'-v','error','-i',str(output),'-f','null','-']).stderr.strip()
run([FF,'-v','error','-y','-i',str(output),'-t','5','-vn',str(OUT/'opening.wav')])
sheet=Image.new('RGB',(1440,680),'#171717'); d=ImageDraw.Draw(sheet)
for i,t in enumerate([.7,3.7,starts[1]+.03,starts[2]+.03]):
    f=OUT/f'qa-{i}.jpg'
    run([FF,'-v','error','-y','-ss',str(t),'-i',str(output),'-frames:v','1','-vf','scale=360:640',str(f)])
    sheet.paste(Image.open(f),(i*360,30)); d.text((i*360+8,8),f'{t:.3f}s',fill='white')
sheet.save(OUT/'review.jpg')
report={'path':str(output),'duration':probe['format']['duration'],'bytes':output.stat().st_size,'video_duration':vs['duration'],'audio_duration':aus['duration'],'source_beats':beats,'riser':[a,end],'click_flash_times':starts[1:-1],'speech_peak':float(np.abs(speech).max()),'effects_peak':float(np.abs(fx).max()),'full_decode':'passed'}
(OUT/'verification.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
