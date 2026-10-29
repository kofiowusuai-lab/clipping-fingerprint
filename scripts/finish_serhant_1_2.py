"""Finish clips 1 and 2 in K's established style, with exact PCM timelines."""
import ast
import json
import math
import re
import statistics
import subprocess
import sys
import wave
from pathlib import Path
import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from src.media.face_detection import YuNetFaceDetector
SOURCE=ROOT/'.local/uploads/youtube-cache/K213Pn9ffIc/full.mp4'
OUT=ROOT/'outputs/serhant-speaker-only'; OUT.mkdir(exist_ok=True)
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
WORDS=json.loads(SOURCE.with_suffix('.transcript_cache.json').read_text())['words']
# The source "I" begins beyond the retained spoken hook; its coarse word
# boundary overlaps the final 50ms of that trim and must not leak into captions.
WORDS=[w for w in WORDS if not (3161220<=w['start']<=3161240 and w['text'].strip().lower()=='i')]
FONT=ImageFont.truetype(str(ROOT/'backend/fonts/Poppins-ExtraBold.ttf'),72)
DETECTOR=YuNetFaceDetector(); CAP=cv2.VideoCapture(str(SOURCE))
tree=ast.parse((ROOT/'scripts/render_serhant_v2.py').read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['run','crop_plan','stamp','captions']]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<render_helpers>','exec'))
SPECS=[
 {'slug':'01-confidence','title':'Confidence is currency','hero':['CONFIDENCE IS','CURRENCY'],
  'beats':[(1550.08,1551.56,1.1),(1558.86,1569.30,1),(1570.10,1575.55,1.1),(1576.15,1586.30,1.16)],
  'transition_after_shots':2,
  'shots':[(1550.08,1551.56,1.1),(1558.86,1563.30,1),(1563.30,1569.30,1.13),(1570.10,1575.55,1.1),(1576.15,1586.30,1.16)]},
 {'slug':'02-negotiation','title':'The best negotiators translate','hero':["DON'T JUST TALK.",'TRANSLATE.'],
  'tail_hold_frames':{0:3,3:3},
  'beats':[(3156.08,3161.28,1.1),(3163.74,3182.41,1),(3187.09,3191.09,1.12)],
  # Drop listener-only passages. A quarter-second onset handle is retained in
  # audio for "employees"; a held incoming guest frame sits under the flash.
  'shots':[(3156.08,3161.28,1.1),(3163.994167,3172.99,1,0.254167),(3172.99,3177.77,1.13),(3177.77,3182.41,1),(3187.09,3191.09,1.12)]},
]

def raw_run(args):
    r=subprocess.run(args,capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode()[-5000:])
    return r

with wave.open(str(ROOT/'outputs/assets/KiJX7agcIns.wav'),'rb') as w:
    riser=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,2)/32768.
energies=[np.mean(riser[i:i+480]**2) for i in range(0,len(riser),480)]
crest_end=(int(np.argmax(energies))+1)*480
results=[]
for spec in SPECS:
    work=OUT/spec['slug']; work.mkdir(exist_ok=True)
    paths=[]; nframes=[]; crops=[]
    for i,shot in enumerate(spec['shots']):
        a,b,punch=shot[:3]; headpad=shot[3] if len(shot)>3 else 0
        n=round((b-a+headpad)*30); plan=crop_plan(a,b,punch)
        part=work/f'part-{i:02d}.mp4'
        vf=f"crop={plan['w']}:{plan['h']}:x='{plan['x']}':y={plan['y']},scale=720:1280:flags=lanczos,setsar=1,fps=30,tpad=start_mode=clone:start_duration={headpad}:stop_mode=clone:stop_duration=0.1"
        tail_hold=spec.get('tail_hold_frames',{}).get(i,0)
        if tail_hold:
            vf+=f',trim=end_frame={n-tail_hold},tpad=stop_mode=clone:stop_duration=0.2'
        raw_run([FFMPEG,'-v','error','-y','-ss',str(a),'-i',str(SOURCE),'-an','-vf',vf,'-frames:v',str(n),'-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',str(part)])
        paths.append(part); nframes.append(n); crops.append({'source':[a,b],'frames':n,'crop':plan})
    listing=work/'concat.txt'; listing.write_text('\n'.join(f"file '{p}'" for p in paths))
    joined=work/'picture.mp4'
    raw_run([FFMPEG,'-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(joined)])
    total_frames=sum(nframes); cut_frame=sum(nframes[:spec.get('transition_after_shots',1)]); cut=cut_frame/30
    # Original speech decoded directly to PCM; only real editorial gaps removed.
    pieces=[]
    for a,b,_ in spec['beats']:
        data=raw_run([FFMPEG,'-v','error','-ss',str(a),'-i',str(SOURCE),'-t',str(b-a),'-vn','-ar','48000','-ac','2','-f','f32le','pipe:1']).stdout
        pieces.append(np.frombuffer(data,dtype='<f4').reshape(-1,2).copy())
    speech=np.concatenate(pieces); target=total_frames*1600
    speech=np.pad(speech,((0,max(0,target-len(speech))),(0,0)))[:target]
    effect=np.zeros_like(speech); at=round(cut*48000); offset=at-crest_end
    assert offset>=0
    swell=riser[:crest_end].copy(); swell[-48:]*=np.linspace(1,0,48)[:,None]
    effect[offset:at]=swell*.28
    mix=speech+effect; peak=np.abs(mix).max()
    if peak>.95: mix*=.95/peak
    wav=work/'mix.wav'
    with wave.open(str(wav),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes((mix*32767).astype('<i2').tobytes())
    ass=work/'captions.ass'; mapped=captions(spec,ass)
    ass.write_text(ass.read_text().replace('Style: Main,Poppins ExtraBold,60,','Style: Main,Poppins ExtraBold,72,'))
    hero=Image.new('RGBA',(720,1280));d=ImageDraw.Draw(hero)
    hf=ImageFont.truetype(str(ROOT/'backend/fonts/BarlowCondensed-Bold.ttf'),76)
    for i,text in enumerate(spec['hero']):
        box=d.textbbox((0,0),text,font=hf,stroke_width=5); width=box[2]-box[0]; assert width<680
        d.text(((720-width)/2-box[0],85+i*82-box[1]),text,font=hf,fill='white' if i==0 else '#FFE000',stroke_width=5,stroke_fill='black')
    hero_path=work/'hero.png';hero.save(hero_path)
    base=work/'captioned.mp4'
    hero_end=min(3.6,cut-.1)
    graph=f"[0:v]subtitles=filename={ass}:fontsdir={ROOT/'backend/fonts'}[base];[base][2:v]overlay=0:0:enable='lt(t,{hero_end})'[v]"
    raw_run([FFMPEG,'-v','error','-y','-i',str(joined),'-i',str(wav),'-i',str(hero_path),'-filter_complex',graph,'-map','[v]','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',str(base)])
    # Same smooth exposure-to-white transition as clip 3, at this clip's cut.
    final=OUT/(spec['slug']+'.mp4')
    cap=cv2.VideoCapture(str(base))
    p=subprocess.Popen([FFMPEG,'-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','720x1280','-r','30','-i','pipe:0','-i',str(base),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','20','-maxrate','1800k','-bufsize','3600k','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(final)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    frame_number=0
    while True:
        ok,f=cap.read()
        if not ok:break
        if cut_frame-3<=frame_number<=cut_frame+8:
            phase=(frame_number-(cut_frame-3))/3 if frame_number<=cut_frame else (cut_frame+8-frame_number)/8
            alpha=(1-np.cos(np.pi*phase))/2
            x=f.astype(np.float32)/255; x=np.minimum(1,x*(1+1.6*alpha)); x=x*(1-alpha**1.45)+alpha**1.45
            f=np.rint(x*255).clip(0,255).astype(np.uint8)
        p.stdin.write(f.tobytes()); frame_number+=1
    cap.release();p.stdin.close();error=p.stderr.read();assert p.wait()==0,error.decode()
    assert frame_number==total_frames
    probe=json.loads(raw_run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(final)]).stdout)
    v=next(s for s in probe['streams'] if s['codec_type']=='video');a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'])==(720,1280)
    assert abs(float(v['duration'])-float(a['duration']))<.05
    assert not raw_run([FFMPEG,'-v','error','-i',str(final),'-f','null','-']).stderr.strip()
    duration=float(probe['format']['duration'])
    times=[.7,cut-.067,cut,cut+.3,duration/2,duration-1]
    sheet=Image.new('RGB',(1080,1340),'#171717');d=ImageDraw.Draw(sheet)
    for i,t in enumerate(times):
        image=work/f'qa-{i}.jpg'; raw_run([FFMPEG,'-v','error','-y','-ss',str(t),'-i',str(final),'-frames:v','1','-vf','scale=360:640',str(image)])
        x=(i%3)*360;y=(i//3)*670;sheet.paste(Image.open(image),(x,y+25));d.text((x+8,y+6),f'{t:.3f}s',fill='white')
    sheet.save(OUT/(spec['slug']+'-review.jpg'))
    raw_run([FFMPEG,'-v','error','-y','-i',str(final),'-t','6','-vn',str(work/'opening.wav')])
    result={'title':spec['title'],'path':str(final),'duration':duration,'bytes':final.stat().st_size,'font':'Poppins ExtraBold','font_size':72,'riser_crest_and_white_flash':cut,'riser_start':offset/48000,'hero':spec['hero'],'audio_beats':spec['beats'],'picture_shots':crops,'transcript':' '.join(w['text'] for w in mapped),'full_decode':'passed'}
    results.append(result);(OUT/'manifest.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='picture_shots'}),flush=True)
assert len(results)==2
