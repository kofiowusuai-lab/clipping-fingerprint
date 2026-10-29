"""Produce hand-selected Dana White shorts in K's established house style."""
import ast
import argparse
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
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from src.media.face_detection import YuNetFaceDetector
SOURCE=ROOT/'.local/uploads/youtube-cache/Q-DFC0AnbY4/full.mp4'
OUT=ROOT/'outputs/dana-white';OUT.mkdir(exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--only');args=parser.parse_args()
FF=imageio_ffmpeg.get_ffmpeg_exe()
FONT=ImageFont.truetype(str(ROOT/'backend/fonts/Poppins-ExtraBold.ttf'),72)
WORDS=json.loads(SOURCE.with_suffix('.transcript_cache.json').read_text())['words']
for w in WORDS:
    w['text']=re.sub(r'>>\s*','',w['text']).strip()
# YouTube's ASR omits this audible word; local Whisper verified it in the source.
for w in WORDS:
    if 677600<=w['start']<=677800 and w['text']=='Bad':w['end']=678040
WORDS.append({'text':'shit','start':678040,'end':678280,'speaker':None})
WORDS.sort(key=lambda w:w['start'])
WORDS=[w for w in WORDS if w['text'] and not re.fullmatch(r'\[[^]]+\]',w['text'])]
DET=YuNetFaceDetector();CAP=cv2.VideoCapture(str(SOURCE))
SPECS=[
 {'slug':'01-time-freedom','title':'Starting a business for more free time?', 'hero':['WANT MORE','FREE TIME?'],
  'ranges':[(706.25,714.15),(671.74,686.24)],
  'shots':[(706.25,714.15,'face',1.10,0),(671.74,673.833343,'card',1,0),(673.833343,678.00,'face',1.0,0),(678.00,682.25001,'face',1.12,0),(682.25001,686.24,'face',1.0,0)]},
 {'slug':'02-build-the-team','title':'No one builds a business alone','hero':["YOU CAN'T DO",'EVERYTHING.'],
  'ranges':[(1223.87,1225.84),(1225.84,1258.50)],
  'shots':[(1223.87,1225.84,'face',1.12,0),(1225.84,1235.84,'face',1.0,0),(1235.84,1243.04,'face',1.10,0),(1243.04,1248.32,'face',1.0,0),(1248.32,1258.50,'face',1.12,0)]},
 {'slug':'03-risk-and-regret','title':"Don't wait for regret",'hero':["DON'T WAIT",'FOR REGRET.'],
  'ranges':[(4272.10,4279.60),(4281.72,4300.46)],
  'shots':[(4272.10,4274.708317,'card',1,0),(4274.708317,4279.60,'face',1.1,0),(4281.72,4290.72,'face',1,0),(4290.72,4299.94,'face',1.12,.52)]},
]

def run(args):
    p=subprocess.run(args,capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode()[-5000:])
    return p

def stamp(t):
    c=round(max(0,t)*100);return f'{c//360000}:{c//6000%60:02d}:{c//100%60:02d}.{c%100:02d}'

def make_captions(spec,path):
    mapped=[];offset=0;boundaries=[]
    for a,b in spec['ranges']:
        for w in WORDS:
            if a*1000<=w['start']<b*1000:
                start=offset+(w['start']/1000-a);end=offset+(min(b,w['end']/1000)-a)
                if end<=start:continue
                mapped.append({'text':w['text'].upper(),'start':start,'end':end})
        offset+=b-a;boundaries.append(offset)
    groups=[];group=[]
    for w in mapped:
        test=' '.join(x['text'] for x in group+[w])
        cross=bool(group) and any(group[-1]['start']<b<=w['start']+.005 for b in boundaries)
        if group and (len(group)>=3 or FONT.getlength(test)>610 or cross or w['start']-group[-1]['end']>.4):groups.append(group);group=[]
        group.append(w)
        if w['text'].endswith(('.', '?','!')):groups.append(group);group=[]
    if group:groups.append(group)
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Poppins ExtraBold,72,&H00FFFFFF,&H0000E8FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,1.5,2,45,45,270,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events=[]
    for gi,g in enumerate(groups):
        following=groups[gi+1][0]['start'] if gi+1<len(groups) else offset
        for i,w in enumerate(g):
            end=g[i+1]['start'] if i+1<len(g) else min(w['end'],following)
            if end<=w['start']:continue
            text=' '.join((r'{\c&H0000E8FF&}' if j==i else r'{\c&H00FFFFFF&}')+x['text'] for j,x in enumerate(g))
            events.append(f'Dialogue: 0,{stamp(w["start"])},{stamp(end)},Main,,0,0,0,,{{\\pos(360,1000)}}'+text)
    path.write_text(header+'\n'.join(events)+'\n')
    return mapped

def crop(a,b,punch):
    faces=[]
    for t in np.linspace(a+.08,max(a+.09,b-.1),max(2,math.ceil(b-a))):
        CAP.set(cv2.CAP_PROP_POS_MSEC,float(t)*1000);ok,frame=CAP.read()
        if not ok:continue
        found=DET.detect(frame)
        if found:faces.append((t-a,max(found,key=lambda f:f[2]*f[3])))
    if not faces:raise RuntimeError(f'No face between {a} and {b}')
    fh=statistics.median(f[3] for _,f in faces)
    h=int(min(1080,max(600,fh*2.8))/punch)//2*2;w=int(h*9/16)//2*2
    y=max(0,min(1080-h,int(min(f[1]-.44*f[3] for _,f in faces))))//2*2
    track=[(t,max(0,min(1920-w,f[0]+f[2]/2-w/2))) for t,f in faces]
    sm=[(t,statistics.mean(p[1] for p in track[max(0,i-1):i+2])) for i,(t,_) in enumerate(track)]
    expr=f'{sm[-1][1]:.2f}'
    for i in range(len(sm)-2,-1,-1):
        t,x=sm[i];nt,nx=sm[i+1];expr=f'if(lt(t,{nt:.4f}),({x:.2f}+({nx-x:.2f})*max(0,t-{t:.4f})/{max(.01,nt-t):.4f}),{expr})'
    return f"crop={w}:{h}:x='{expr}':y={y},scale=720:1280:flags=lanczos,setsar=1",{'width':w,'height':h,'y':y,'face_count':len(faces)}

with wave.open(str(ROOT/'outputs/assets/KiJX7agcIns.wav'),'rb') as w:riser=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,2)/32768.
crest=(int(np.argmax([np.mean(riser[i:i+480]**2) for i in range(0,len(riser),480)]))+1)*480
manifest=json.loads((OUT/'manifest.json').read_text()) if args.only and (OUT/'manifest.json').exists() else []
for spec in SPECS:
    if args.only and spec['slug']!=args.only:continue
    work=OUT/spec['slug'];work.mkdir(exist_ok=True)
    parts=[];counts=[];plans=[]
    for i,(a,b,mode,punch,tail) in enumerate(spec['shots']):
        n=round((b-a+tail)*30)
        if mode=='card':vf='scale=720:406:flags=lanczos,pad=720:1280:0:390:black,setsar=1';plan={'kind':'original-source quote card preserved in full'}
        else:vf,plan=crop(a,b,punch)
        # Trim the real picture before a camera cut, then hold only the final
        # closing syllable rather than introducing a sub-second listener flash.
        vf+=',fps=30'
        if tail:vf+=f',trim=end_frame={round((b-a)*30)},tpad=stop_mode=clone:stop_duration={tail+.1}'
        else:vf+=',tpad=stop_mode=clone:stop_duration=0.1'
        part=work/f'part-{i:02d}.mp4'
        run([FF,'-v','error','-y','-ss',str(a),'-i',str(SOURCE),'-an','-vf',vf,'-frames:v',str(n),'-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',str(part)])
        parts.append(part);counts.append(n);plans.append({'source':[a,b],'mode':mode,'punch':punch,'tail_hold':tail,'frames':n,**plan})
    listing=work/'concat.txt';listing.write_text('\n'.join(f"file '{p}'" for p in parts))
    picture=work/'picture.mp4';run([FF,'-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(picture)])
    cut=round((spec['ranges'][0][1]-spec['ranges'][0][0])*30)/30
    # First range is the semantic opening hook, including all original camera
    # shots: its end, not an arbitrary punch-in, determines the effect cue.
    pieces=[]
    for a,b in spec['ranges']:
        raw=run([FF,'-v','error','-ss',str(a),'-i',str(SOURCE),'-t',str(b-a),'-vn','-ar','48000','-ac','2','-f','f32le','pipe:1']).stdout
        pieces.append(np.frombuffer(raw,dtype='<f4').reshape(-1,2).copy())
    speech=np.concatenate(pieces);target=sum(counts)*1600
    speech=np.pad(speech,((0,max(0,target-len(speech))),(0,0)))[:target]
    fx=np.zeros_like(speech);end=round(cut*48000);start=end-crest;assert start>=0
    swell=riser[:crest].copy();swell[-48:]*=np.linspace(1,0,48)[:,None];fx[start:end]=swell*.28
    mix=speech+fx;peak=np.max(np.abs(mix))
    if peak>.95:mix*=.95/peak
    wav=work/'mix.wav'
    with wave.open(str(wav),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes((mix*32767).astype('<i2').tobytes())
    ass=work/'captions.ass';mapped=make_captions(spec,ass)
    hero=Image.new('RGBA',(720,1280));d=ImageDraw.Draw(hero);hf=ImageFont.truetype(str(ROOT/'backend/fonts/BarlowCondensed-Bold.ttf'),76)
    for i,text in enumerate(spec['hero']):
        box=d.textbbox((0,0),text,font=hf,stroke_width=5);width=box[2]-box[0];assert width<680
        d.text(((720-width)/2-box[0],85+i*82-box[1]),text,font=hf,fill='white' if i==0 else '#FFE000',stroke_width=5,stroke_fill='black')
    hp=work/'hero.png';hero.save(hp)
    base=work/'captioned.mp4';hero_end=min(3.6,cut-.1)
    graph=f"[0:v]subtitles=filename={ass}:fontsdir={ROOT/'backend/fonts'}[base];[base][2:v]overlay=0:0:enable='lt(t,{hero_end})'[v]"
    run([FF,'-v','error','-y','-i',str(picture),'-i',str(wav),'-i',str(hp),'-filter_complex',graph,'-map','[v]','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',str(base)])
    final=OUT/(spec['slug']+'.mp4')
    subprocess.run([sys.executable,str(ROOT/'scripts/add_white_luma_flash.py'),'--source',str(base),'--output-dir',str(work),'--output-name',str(final),'--cut-seconds',str(cut)],check=True)
    probe=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(final)]).stdout)
    duration=float(probe['format']['duration']);v=next(s for s in probe['streams'] if s['codec_type']=='video');audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'])==(720,1280)
    assert abs(float(v['duration'])-float(audio['duration']))<.05
    sheet=Image.new('RGB',(1440,1340),'#171717');d=ImageDraw.Draw(sheet)
    cumulative=np.cumsum(counts)/30
    times=[.8,cut-.1,cut,cut+.35,duration*.5,duration-1,duration-.2,min(duration-.1,cumulative[0]+.05)]
    for i,t in enumerate(times):
        image=work/f'qa-{i}.jpg';run([FF,'-v','error','-y','-ss',str(t),'-i',str(final),'-frames:v','1','-vf','scale=360:640',str(image)])
        x=i%4*360;y=i//4*670;sheet.paste(Image.open(image),(x,y+25));d.text((x+8,y+6),f'{t:.3f}s',fill='white')
    sheet.save(OUT/(spec['slug']+'-review.jpg'))
    run([FF,'-v','error','-y','-i',str(final),'-vn',str(work/'final-audio.wav')])
    result={'title':spec['title'],'path':str(final),'duration':duration,'bytes':final.stat().st_size,'source_url':'https://youtu.be/Q-DFC0AnbY4?is=rIqehB23FVSC4hHE','audio_ranges':spec['ranges'],'picture_shots':plans,'riser_start':start/48000,'riser_crest_and_white_flash':cut,'hero':spec['hero'],'transcript':' '.join(w['text'] for w in mapped),'full_decode':'passed'}
    manifest=[old for old in manifest if old['path']!=result['path']]
    manifest.append(result);manifest.sort(key=lambda s:s['path']);(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='picture_shots'}),flush=True)
assert len(manifest)==3
