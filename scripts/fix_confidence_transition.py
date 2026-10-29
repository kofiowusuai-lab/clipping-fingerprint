"""Put clip 1's riser and white flash on the completed hook, never mid-sentence."""
import json
import re
import subprocess
import sys
import wave
from pathlib import Path
import imageio_ffmpeg
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'outputs/serhant-speaker-only'
OUT=ROOT/'outputs/serhant-confidence-timed';OUT.mkdir(exist_ok=True)
FF=imageio_ffmpeg.get_ffmpeg_exe()
SOURCE=ROOT/'.local/uploads/youtube-cache/K213Pn9ffIc/full.mp4'
manifest=json.loads((OLD/'manifest.json').read_text())[0]
LEAD=.4
CUT_FRAMES=round((1551.56-1550.08)*30)+round(LEAD*30)
CUT=CUT_FRAMES/30

def run(args):
    p=subprocess.run(args,capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode()[-5000:])
    return p

def parse_time(s):
    h,m,s=map(float,s.split(':'));return h*3600+m*60+s

def stamp(t):
    c=round(t*100);return f'{c//360000}:{c//6000%60:02d}:{c//100%60:02d}.{c%100:02d}'

# Rebuild from a clean picture and clean source speech, not the export with FX.
lines=[]
for line in (OLD/'01-confidence/captions.ass').read_text().splitlines():
    if line.startswith('Dialogue:'):
        fields=line.split(',',9)
        fields[1]=stamp(parse_time(fields[1])+LEAD);fields[2]=stamp(parse_time(fields[2])+LEAD)
        line=','.join(fields)
    lines.append(line)
ass=OUT/'captions.ass';ass.write_text('\n'.join(lines)+'\n')
pieces=[]
for a,b,_ in manifest['audio_beats']:
    raw=run([FF,'-v','error','-ss',str(a),'-i',str(SOURCE),'-t',str(b-a),'-vn','-ar','48000','-ac','2','-f','f32le','pipe:1']).stdout
    pieces.append(np.frombuffer(raw,dtype='<f4').reshape(-1,2).copy())
speech=np.concatenate(pieces)
original_frames=round(manifest['duration']*30)
target=original_frames*1600
speech=np.pad(speech,((0,max(0,target-len(speech))),(0,0)))[:target]
speech=np.concatenate([np.zeros((round(LEAD*48000),2)),speech])
with wave.open(str(ROOT/'outputs/assets/KiJX7agcIns.wav'),'rb') as w:
    riser=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,2)/32768.
energies=[np.mean(riser[i:i+480]**2) for i in range(0,len(riser),480)]
crest_end=(int(np.argmax(energies))+1)*480
at=round(CUT*48000);offset=at-crest_end;assert offset>=0
fx=np.zeros_like(speech);swell=riser[:crest_end].copy();swell[-48:]*=np.linspace(1,0,48)[:,None];fx[offset:at]=swell*.28
assert not fx[at:].any()
mix=speech+fx
if np.max(np.abs(mix))>.95:mix*=.95/np.max(np.abs(mix))
wav=OUT/'mix.wav'
with wave.open(str(wav),'wb') as w:
    w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes((mix*32767).astype('<i2').tobytes())
hero=OLD/'01-confidence/hero.png'
base=OUT/'captioned-clean.mp4'
graph=f"[0:v]tpad=start_mode=clone:start_duration={LEAD},subtitles=filename={ass}:fontsdir={ROOT/'backend/fonts'}[base];[base][2:v]overlay=0:0:enable='lt(t,{CUT-.1})'[v]"
run([FF,'-v','error','-y','-i',str(OLD/'01-confidence/picture.mp4'),'-i',str(wav),'-i',str(hero),'-filter_complex',graph,'-map','[v]','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',str(base)])
subprocess.run([sys.executable,str(ROOT/'scripts/add_white_luma_flash.py'),'--source',str(base),'--output-dir',str(OUT),'--output-name','01-confidence-hook-transition.mp4','--cut-seconds',str(CUT)],check=True)
final=OUT/'01-confidence-hook-transition.mp4'
run([FF,'-v','error','-y','-i',str(final),'-t','6','-vn',str(OUT/'opening.wav')])
sheet=Image.new('RGB',(1440,680),'#171717');d=ImageDraw.Draw(sheet)
for i,t in enumerate([CUT-.133,CUT,CUT+.333,6.3]):
    image=OUT/f'qa-{i}.jpg';run([FF,'-v','error','-y','-ss',str(t),'-i',str(final),'-frames:v','1','-vf','scale=360:640',str(image)])
    sheet.paste(Image.open(image),(i*360,25));d.text((i*360+8,6),f'{t:.3f}s',fill='white')
sheet.save(OUT/'semantic-transition-review.jpg')
report={'path':str(final),'hook':'Confidence is currency.','lead_in':LEAD,'transition_at':CUT,'source_hook_end':1551.56,'riser_start':offset/48000,'riser_crest':CUT,'previous_mid_sentence_flash_removed':5.9+LEAD,'following_sentence':'Because they can pay for whatever information or whatever access they want.'}
(OUT/'timing.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
